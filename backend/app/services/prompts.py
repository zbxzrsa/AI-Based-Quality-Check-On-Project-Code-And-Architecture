"""
Prompt engineering templates for AI code review
"""

SYSTEM_PROMPT = """You are an expert code reviewer with deep knowledge of software engineering best practices, security vulnerabilities, design patterns, and performance optimization.

Your task is to analyze code changes in pull requests and provide comprehensive, actionable feedback.

Focus on:
1. **Security**: SQL injection, XSS, authentication/authorization issues, data exposure
2. **Logic**: Edge cases, error handling, null/undefined checks, race conditions
3. **Architecture**: Design pattern violations, tight coupling, separation of concerns
4. **Performance**: O(n²) algorithms, N+1 queries, memory leaks, inefficient data structures
5. **Code Quality**: Naming conventions, complexity, duplication, readability

Output must be valid JSON with this exact structure:
{
  "issues": [
    {
      "type": "security|logic|architecture|performance|quality",
      "severity": "critical|high|medium|low|info",
      "confidence": 0-100,
      "file": "relative/path/to/file.ext",
      "line": line_number,
      "title": "Brief issue description (max 100 chars)",
      "description": "Detailed explanation with context",
      "suggestion": "Specific actionable fix",
      "example": "Code example showing the fix (optional)"
    }
  ],
  "summary": "Overall assessment of the PR quality and risk",
  "risk_score": 0-100
}

Severity Guidelines:
- **critical**: Security vulnerabilities, data loss, system crashes
- **high**: Logic errors causing incorrect behavior, performance degradation
- **medium**: Code quality issues, minor bugs, suboptimal patterns
- **low**: Style issues, minor optimizations
- **info**: Suggestions for improvement

Be concise but thorough. Prioritize actionable feedback over theoretical concerns."""


def create_code_review_prompt(
    repo_name: str,
    pr_title: str,
    pr_description: str,
    file_count: int,
    diff: str,
    dependency_context: str = "",
    baseline_rules: str = "",
    language: str = "Python"
) -> str:
    """
    Create user prompt for code review
    
    Args:
        repo_name: Repository name
        pr_title: Pull request title
        pr_description: PR description
        file_count: Number of files changed
        diff: Git diff content
        dependency_context: Dependency graph summary
        baseline_rules: Architectural constraints
        language: Primary language
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""# Code Review Request

## Context
- **Repository**: {repo_name}
- **Pull Request**: {pr_title}
- **Description**: {pr_description or "No description provided"}
- **Files Changed**: {file_count}
- **Primary Language**: {language}

"""
    
    if dependency_context:
        prompt += f"""## Architectural Context
{dependency_context}

"""
    
    if baseline_rules:
        prompt += f"""## Architectural Rules
{baseline_rules}

"""
    
    prompt += f"""## Code Changes

```diff
{diff}
```

## Instructions

Analyze the code changes above and provide a comprehensive review covering:

1. **Security vulnerabilities** (highest priority)
2. **Logic errors and edge cases**
3. **Architectural violations**
4. **Performance concerns**
5. **Code quality issues**

For each issue found:
- Specify the exact file and line number
- Assign appropriate severity
- Provide confidence score (how certain you are)
- Give specific, actionable suggestions
- Include code examples for fixes when applicable

Also provide:
- Overall risk score (0-100) for this PR
- Summary of the review

Remember to output valid JSON only, following the specified schema.
"""
    
    return prompt


FEW_SHOT_EXAMPLES = """
## Example 1: Security Issue

```python
# Bad Code
user_input = request.GET['username']
query = f"SELECT * FROM users WHERE username = '{user_input}'"
cursor.execute(query)
```

**Issue**:
```json
{
  "type": "security",
  "severity": "critical",
  "confidence": 100,
  "file": "api/auth.py",
  "line": 42,
  "title": "SQL Injection vulnerability in user authentication",
  "description": "Direct string interpolation of user input into SQL query allows SQL injection attacks. An attacker could input malicious SQL to bypass authentication or access unauthorized data.",
  "suggestion": "Use parameterized queries or ORM to prevent SQL injection",
  "example": "cursor.execute('SELECT * FROM users WHERE username = %s', (user_input,))"
}
```

## Example 2: Performance Issue

```python
# Bad Code
for user in users:
    user.posts = Post.objects.filter(user_id=user.id)  # N+1 query
```

**Issue**:
```json
{
  "type": "performance",
  "severity": "high",
  "confidence": 95,
  "file": "views/dashboard.py",
  "line": 28,
  "title": "N+1 query problem in user dashboard",
  "description": "Fetching posts individually for each user results in N+1 database queries. For 100 users, this causes 101 queries instead of 2.",
  "suggestion": " Use select_related or prefetch_related to fetch posts in a single query",
  "example": "users = User.objects.prefetch_related('posts')"
}
```

## Example 3: Logic Error

```python
# Bad Code
def calculate_discount(price, discount_percent):
    return price - (price * discount_percent)  # Missing division by 100
```

**Issue**:
```json
{
  "type": "logic",
  "severity": "high",
  "confidence": 100,
  "file": "utils/pricing.py",
  "line": 15,
  "title": "Incorrect discount calculation",
  "description": "Discount percentage is not converted to decimal. For discount_percent=20, this calculates 20x the price instead of 20%.",
  "suggestion": "Divide discount_percent by 100 to convert to decimal",
  "example": "return price - (price * discount_percent / 100)"
}
```
"""


SECURITY_FOCUSED_PROMPT = """Focus specifically on security vulnerabilities:

- **Injection Attacks**: SQL, NoSQL, Command, LDAP injection
- **Authentication**: Weak passwords, missing validation, session fixation
- **Authorization**: Missing access controls, privilege escalation
- **Cryptography**: Weak algorithms, hardcoded keys, insecure random
- **Data Exposure**: Sensitive data in logs, error messages, URLs
- **XSS**: Reflected, stored, DOM-based
- **CSRF**: Missing tokens, improper validation
- **Deserialization**: Unsafe object deserialization
- **Dependencies**: Known vulnerable libraries
- **Configuration**: Debug mode in production, exposed secrets

Mark all security issues as high or critical severity."""


PERFORMANCE_FOCUSED_PROMPT = """Focus specifically on performance concerns:

- **Database**: N+1 queries, missing indexes, inefficient joins
- **Algorithms**: O(n²) or worse complexity, unnecessary iterations
- **Memory**: Memory leaks, large object allocation, caching issues
- **I/O**: Synchronous blocking calls, excessive file operations
- **Network**: Chatty APIs, missing pagination, large payloads
- **Concurrency**: Race conditions, deadlocks, inefficient locking

Provide complexity analysis (Big O) where applicable."""


ARCHITECTURE_FOCUSED_PROMPT = """Focus specifically on architectural concerns:

- **SOLID Principles**: Violations of Single Responsibility, Open/Closed, etc.
- **Design Patterns**: Misuse or absence of appropriate patterns
- **Coupling**: Tight coupling between modules
- **Cohesion**: Low cohesion within modules
- **Separation of Concerns**: Mixed responsibilities
- **Dependency Direction**: Violations of dependency rules
- **Layer Violations**: Business logic in presentation layer, etc.
- **Code Duplication**: Repeated logic that should be abstracted

Reference the dependency graph context to identify violations."""


def create_specialized_prompt(
    focus: str,
    repo_name: str,
    pr_title: str,
    diff: str,
    **kwargs
) -> tuple[str, str]:
    """
    Create specialized review prompt
    
    Args:
        focus: 'security', 'performance', or 'architecture'
        repo_name: Repository name
        pr_title: PR title
        diff: Diff content
        **kwargs: Additional context
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    base_system = SYSTEM_PROMPT
    
    if focus == "security":
        system_prompt = base_system + "\n\n" + SECURITY_FOCUSED_PROMPT
    elif focus == "performance":
        system_prompt = base_system + "\n\n" + PERFORMANCE_FOCUSED_PROMPT
    elif focus == "architecture":
        system_prompt = base_system + "\n\n" + ARCHITECTURE_FOCUSED_PROMPT
    else:
        system_prompt = base_system
    
    user_prompt = create_code_review_prompt(
        repo_name=repo_name,
        pr_title=pr_title,
        diff=diff,
        **kwargs
    )
    
    return system_prompt, user_prompt


def truncate_diff_smart(diff: str, max_lines: int = 500) -> str:
    """
    Intelligently truncate diff to fit context window
    
    Prioritizes:
    1. Added/modified lines over context
    2. Beginning and end of files
    3. Removed duplicate hunks
    
    Args:
        diff: Git diff content
        max_lines: Maximum lines to include
        
    Returns:
        Truncated diff
    """
    lines = diff.split('\n')
    
    if len(lines) <= max_lines:
        return diff
    
    # Keep file headers and changed lines
    important_lines = []
    for line in lines:
        if (line.startswith('diff --git') or
            line.startswith('+++') or
            line.startswith('---') or
            line.startswith('@@') or
            line.startswith('+') or
            line.startswith('-')):
            important_lines.append(line)
        elif len(important_lines) < max_lines:
            # Keep some context
            important_lines.append(line)
    
    if len(important_lines) > max_lines:
        important_lines = important_lines[:max_lines]
        important_lines.append("\n... (diff truncated for context limit)")
    
    return '\n'.join(important_lines)
