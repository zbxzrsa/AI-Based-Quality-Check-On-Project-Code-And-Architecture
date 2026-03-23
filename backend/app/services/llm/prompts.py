"""
Code Analysis Prompts

Provides structured prompts for LLM-based code analysis including
code quality review, architectural analysis, and security vulnerability detection.

Validates Requirements: 1.4
"""
import logging
logger = logging.getLogger(__name__)


from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass


class AnalysisType(str, Enum):
    """Types of code analysis"""
    CODE_QUALITY = "code_quality"
    ARCHITECTURE = "architecture"
    SECURITY = "security"


@dataclass
class PromptTemplate:
    """Template for code analysis prompts"""
    system_prompt: str
    user_prompt_template: str
    analysis_type: AnalysisType
    
    def format(self, **kwargs) -> Dict[str, str]:
        """
        Format the prompt template with provided variables.
        
        Args:
            **kwargs: Variables to substitute in the template
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt' keys
            
        Raises:
            KeyError: If required template variables are missing
        """
        try:
            user_prompt = self.user_prompt_template.format(**kwargs)
            return {
                "system_prompt": self.system_prompt,
                "user_prompt": user_prompt
            }
        except KeyError as e:
            raise KeyError(
                f"Missing required template variable: {e}. "
                f"Available variables: {list(kwargs.keys())}"
            )


class CodeAnalysisPrompts:
    """
    Prompt library for code analysis.
    
    Provides well-designed prompts for different types of code analysis:
    - Code quality review (readability, maintainability, best practices)
    - Architectural analysis (design patterns, dependencies, structure)
    - Security vulnerability detection (OWASP Top 10, secure coding)
    
    Validates Requirements: 1.4
    """
    
    # Code Quality Review Prompts
    CODE_QUALITY_SYSTEM = """You are an expert code reviewer specializing in code quality, readability, and maintainability.

Your role is to analyze code changes and provide constructive, actionable feedback that helps developers write better code.

Focus on:
- Code readability and clarity
- Adherence to language-specific best practices and idioms
- Maintainability and code organization
- Proper error handling and edge cases
- Code duplication and opportunities for refactoring
- Naming conventions and documentation
- Performance considerations (only critical issues)

Guidelines:
- Be specific and cite line numbers when possible
- Provide concrete suggestions for improvement
- Explain WHY something is an issue, not just WHAT is wrong
- Prioritize issues by severity (critical, high, medium, low)
- Be constructive and encouraging, not harsh
- Focus on the most impactful improvements
- Avoid nitpicking minor style issues unless they affect readability

Output Format:
Provide your review as a structured list of findings. For each finding:
1. Severity: [critical/high/medium/low]
2. Location: File path and line number(s)
3. Issue: Clear description of the problem
4. Suggestion: Specific recommendation for improvement
5. Rationale: Brief explanation of why this matters"""

    CODE_QUALITY_USER = """Review the following code changes for quality, readability, and maintainability.

**File:** {file_path}

**Language:** {language}

**Code Changes:**
```{language}
{code_diff}
```

**Context:** {context}

Please provide a thorough code quality review focusing on readability, maintainability, best practices, and potential improvements."""

    # Architectural Analysis Prompts
    ARCHITECTURE_SYSTEM = """You are a senior software architect specializing in system design, architectural patterns, and code structure.

Your role is to analyze code changes from an architectural perspective and identify potential design issues, architectural drift, and opportunities for improvement.

Focus on:
- Design patterns and architectural principles (SOLID, DRY, KISS)
- Component coupling and cohesion
- Dependency management and circular dependencies
- Separation of concerns and layering
- API design and interface contracts
- Scalability and extensibility considerations
- Architectural consistency with existing codebase
- Technical debt and refactoring opportunities

Guidelines:
- Consider the broader system context, not just individual files
- Identify architectural smells and anti-patterns
- Suggest architectural improvements with clear benefits
- Highlight deviations from established architectural patterns
- Consider long-term maintainability and evolution
- Prioritize issues by architectural impact
- Be pragmatic - balance ideal architecture with practical constraints

Output Format:
Provide your architectural analysis as a structured list of findings. For each finding:
1. Severity: [critical/high/medium/low]
2. Location: Component/module/file affected
3. Issue: Clear description of the architectural concern
4. Impact: How this affects the system architecture
5. Suggestion: Recommended architectural improvement
6. Rationale: Why this architectural change matters"""

    ARCHITECTURE_USER = """Analyze the following code changes from an architectural perspective.

**File:** {file_path}

**Language:** {language}

**Code Changes:**
```{language}
{code_diff}
```

**Existing Dependencies:**
{dependencies}

**Architectural Context:** {context}

Please provide an architectural analysis focusing on design patterns, dependencies, component structure, and alignment with architectural principles."""

    # Security Vulnerability Detection Prompts
    SECURITY_SYSTEM = """You are a security expert specializing in application security, vulnerability detection, and secure coding practices.

Your role is to analyze code changes for security vulnerabilities, insecure patterns, and potential attack vectors.

Focus on OWASP Top 10 and common security issues:
1. Injection flaws (SQL, NoSQL, Command, LDAP, XPath)
2. Broken authentication and session management
3. Sensitive data exposure
4. XML External Entities (XXE)
5. Broken access control
6. Security misconfiguration
7. Cross-Site Scripting (XSS)
8. Insecure deserialization
9. Using components with known vulnerabilities
10. Insufficient logging and monitoring

Additional security concerns:
- Input validation and sanitization
- Output encoding
- Cryptographic issues (weak algorithms, hardcoded keys)
- Race conditions and concurrency issues
- Information disclosure
- Insecure direct object references
- CSRF vulnerabilities
- Security headers and configurations

Guidelines:
- Identify specific vulnerabilities with CVE/CWE references when applicable
- Explain the potential attack vector and impact
- Provide secure coding alternatives
- Consider the severity based on exploitability and impact
- Reference OWASP guidelines and security best practices
- Be thorough but avoid false positives
- Consider the context (e.g., internal vs. public-facing)

Output Format:
Provide your security analysis as a structured list of findings. For each finding:
1. Severity: [critical/high/medium/low]
2. Vulnerability Type: OWASP category or CWE identifier
3. Location: File path and line number(s)
4. Issue: Clear description of the security vulnerability
5. Attack Vector: How this could be exploited
6. Impact: Potential consequences of exploitation
7. Remediation: Specific steps to fix the vulnerability
8. References: Links to OWASP/CWE documentation"""

    SECURITY_USER = """Analyze the following code changes for security vulnerabilities and insecure coding practices.

**File:** {file_path}

**Language:** {language}

**Code Changes:**
```{language}
{code_diff}
```

**Security Context:** {context}

**Exposure Level:** {exposure_level}

Please provide a comprehensive security analysis focusing on OWASP Top 10 vulnerabilities, injection flaws, authentication issues, data exposure, and other security concerns."""

    @classmethod
    def get_code_quality_prompt(
        cls,
        file_path: str,
        language: str,
        code_diff: str,
        context: str = "Pull request code review"
    ) -> Dict[str, str]:
        """
        Get code quality review prompt.
        
        Args:
            file_path: Path to the file being reviewed
            language: Programming language
            code_diff: Code changes to review
            context: Additional context about the changes
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
        """
        template = PromptTemplate(
            system_prompt=cls.CODE_QUALITY_SYSTEM,
            user_prompt_template=cls.CODE_QUALITY_USER,
            analysis_type=AnalysisType.CODE_QUALITY
        )
        
        return template.format(
            file_path=file_path,
            language=language,
            code_diff=code_diff,
            context=context
        )
    
    @classmethod
    def get_architecture_prompt(
        cls,
        file_path: str,
        language: str,
        code_diff: str,
        dependencies: str = "No dependencies provided",
        context: str = "Architectural review"
    ) -> Dict[str, str]:
        """
        Get architectural analysis prompt.
        
        Args:
            file_path: Path to the file being reviewed
            language: Programming language
            code_diff: Code changes to review
            dependencies: Existing dependencies information
            context: Additional architectural context
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
        """
        template = PromptTemplate(
            system_prompt=cls.ARCHITECTURE_SYSTEM,
            user_prompt_template=cls.ARCHITECTURE_USER,
            analysis_type=AnalysisType.ARCHITECTURE
        )
        
        return template.format(
            file_path=file_path,
            language=language,
            code_diff=code_diff,
            dependencies=dependencies,
            context=context
        )
    
    @classmethod
    def get_security_prompt(
        cls,
        file_path: str,
        language: str,
        code_diff: str,
        context: str = "Security vulnerability scan",
        exposure_level: str = "public-facing"
    ) -> Dict[str, str]:
        """
        Get security vulnerability detection prompt.
        
        Args:
            file_path: Path to the file being reviewed
            language: Programming language
            code_diff: Code changes to review
            context: Security context
            exposure_level: Exposure level (public-facing, internal, private)
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
        """
        template = PromptTemplate(
            system_prompt=cls.SECURITY_SYSTEM,
            user_prompt_template=cls.SECURITY_USER,
            analysis_type=AnalysisType.SECURITY
        )
        
        return template.format(
            file_path=file_path,
            language=language,
            code_diff=code_diff,
            context=context,
            exposure_level=exposure_level
        )
    
    @classmethod
    def get_prompt_by_type(
        cls,
        analysis_type: AnalysisType,
        **kwargs
    ) -> Dict[str, str]:
        """
        Get prompt by analysis type.
        
        Args:
            analysis_type: Type of analysis to perform
            **kwargs: Variables for prompt template
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
            
        Raises:
            ValueError: If analysis_type is not supported
        """
        if analysis_type == AnalysisType.CODE_QUALITY:
            return cls.get_code_quality_prompt(**kwargs)
        elif analysis_type == AnalysisType.ARCHITECTURE:
            return cls.get_architecture_prompt(**kwargs)
        elif analysis_type == AnalysisType.SECURITY:
            return cls.get_security_prompt(**kwargs)
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")


class PromptManager:
    """
    Manager for code analysis prompts.
    
    Provides a high-level interface for generating prompts for different
    types of code analysis with proper variable substitution and validation.
    
    Validates Requirements: 1.4
    """
    
    def __init__(self):
        """Initialize prompt manager"""
        self.prompts = CodeAnalysisPrompts()
    
    def generate_prompt(
        self,
        analysis_type: AnalysisType,
        file_path: str,
        language: str,
        code_diff: str,
        **kwargs
    ) -> Dict[str, str]:
        """
        Generate a prompt for code analysis.
        
        Args:
            analysis_type: Type of analysis (code_quality, architecture, security)
            file_path: Path to the file being analyzed
            language: Programming language
            code_diff: Code changes to analyze
            **kwargs: Additional context variables
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
            
        Example:
            >>> manager = PromptManager()
            >>> prompt = manager.generate_prompt(
            ...     analysis_type=AnalysisType.CODE_QUALITY,
            ...     file_path="src/auth.py",
            ...     language="python",
            ...     code_diff="def login(user, password): ...",
            ...     context="Authentication module review"
            ... )
            >>> logger.info(str(prompt['system_prompt']))
            >>> logger.info(str(prompt['user_prompt']))
        """
        return self.prompts.get_prompt_by_type(
            analysis_type=analysis_type,
            file_path=file_path,
            language=language,
            code_diff=code_diff,
            **kwargs
        )
    
    def generate_code_quality_prompt(
        self,
        file_path: str,
        language: str,
        code_diff: str,
        context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate code quality review prompt.
        
        Args:
            file_path: Path to the file being reviewed
            language: Programming language
            code_diff: Code changes to review
            context: Optional additional context
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
        """
        kwargs = {"context": context} if context else {}
        return self.prompts.get_code_quality_prompt(
            file_path=file_path,
            language=language,
            code_diff=code_diff,
            **kwargs
        )
    
    def generate_architecture_prompt(
        self,
        file_path: str,
        language: str,
        code_diff: str,
        dependencies: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate architectural analysis prompt.
        
        Args:
            file_path: Path to the file being reviewed
            language: Programming language
            code_diff: Code changes to review
            dependencies: Optional dependencies information
            context: Optional architectural context
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
        """
        kwargs = {}
        if dependencies:
            kwargs["dependencies"] = dependencies
        if context:
            kwargs["context"] = context
        
        return self.prompts.get_architecture_prompt(
            file_path=file_path,
            language=language,
            code_diff=code_diff,
            **kwargs
        )
    
    def generate_security_prompt(
        self,
        file_path: str,
        language: str,
        code_diff: str,
        context: Optional[str] = None,
        exposure_level: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate security vulnerability detection prompt.
        
        Args:
            file_path: Path to the file being reviewed
            language: Programming language
            code_diff: Code changes to review
            context: Optional security context
            exposure_level: Optional exposure level (public-facing, internal, private)
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
        """
        kwargs = {}
        if context:
            kwargs["context"] = context
        if exposure_level:
            kwargs["exposure_level"] = exposure_level
        
        return self.prompts.get_security_prompt(
            file_path=file_path,
            language=language,
            code_diff=code_diff,
            **kwargs
        )
    
    def get_available_analysis_types(self) -> List[str]:
        """
        Get list of available analysis types.
        
        Returns:
            List of analysis type names
        """
        return [t.value for t in AnalysisType]


# Convenience function for quick access
def get_prompt_manager() -> PromptManager:
    """
    Get a prompt manager instance.
    
    Returns:
        PromptManager instance
        
    Example:
        >>> manager = get_prompt_manager()
        >>> prompt = manager.generate_code_quality_prompt(
        ...     file_path="src/auth.py",
        ...     language="python",
        ...     code_diff="..."
        ... )
    """
    return PromptManager()
