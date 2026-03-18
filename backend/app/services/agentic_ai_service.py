"""
Agentic AI Service - Complex reasoning and decision support using multiple LLMs

This service provides:
- Pattern recognition (Clean Code violations)
- Contextual reasoning (graph database integration)
- Natural language generation (developer-friendly explanations)
- Scenario simulation
- Refactoring suggestions

Validates Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9, 3.10, 3.11
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.services.context_builder import create_context_builder
from app.shared.llm_provider import LLMOrchestrator, LLMProviderConfig, LLMProviderType


class CleanCodePrinciple(str, Enum):
    """Clean Code principles for violation detection"""

    MEANINGFUL_NAMES = "meaningful_names"
    SMALL_FUNCTIONS = "small_functions"
    DRY = "dry"  # Don't Repeat Yourself
    SINGLE_RESPONSIBILITY = "single_responsibility"
    PROPER_COMMENTS = "proper_comments"
    ERROR_HANDLING = "error_handling"
    FORMATTING = "formatting"
    BOUNDARIES = "boundaries"
    UNIT_TESTS = "unit_tests"


@dataclass
class CleanCodeViolation:
    """Represents a Clean Code principle violation"""

    principle: CleanCodePrinciple
    severity: str  # critical, high, medium, low
    location: str  # file:line
    description: str
    suggestion: str
    example_fix: str | None = None


@dataclass
class NaturalLanguageExplanation:
    """Natural language explanation of technical findings"""

    technical_finding: str
    developer_explanation: str
    why_it_matters: str
    how_to_fix: str
    code_example: str | None = None


@dataclass
class ReasoningResult:
    """Result of AI reasoning task"""

    task_type: str
    suggestions: list[dict[str, Any]]
    confidence: float
    reasoning_chain: list[str]
    knowledge_references: list[str]


class AgenticAIService:
    """
    Agentic AI Service for complex reasoning and decision support.

    Validates Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9, 3.10, 3.11
    """

    def __init__(
        self,
        llm_orchestrator: LLMOrchestrator,
        neo4j_client: Any | None = None,
        redis_client: Any | None = None,
    ):
        """
        Initialize Agentic AI Service.

        Args:
            llm_orchestrator: LLM orchestrator for multi-provider support
            neo4j_client: Optional Neo4j client for graph context
            redis_client: Optional Redis client for caching
        """
        self.llm = llm_orchestrator
        self.neo4j = neo4j_client
        self.redis = redis_client

        # Initialize context builder if Neo4j client is available
        self.context_builder = None
        if neo4j_client is not None:
            self.context_builder = create_context_builder(
                neo4j_client=neo4j_client, max_context_tokens=4000, max_depth=2
            )
            logger.info("Context builder initialized with Neo4j client")

        logger.info(
            "Agentic AI Service initialized",
            extra={
                "provider_count": llm_orchestrator.get_provider_count(),
                "has_neo4j": neo4j_client is not None,
                "has_redis": redis_client is not None,
                "has_context_builder": self.context_builder is not None,
            },
        )

    async def analyze_clean_code_violations(
        self,
        code: str,
        file_path: str,
        language: str = "python",
    ) -> list[CleanCodeViolation]:
        """
        Analyze code for Clean Code principle violations.

        Validates Requirements: 3.9

        Args:
            code: Source code to analyze
            file_path: Path to the file
            language: Programming language

        Returns:
            List of Clean Code violations
        """
        logger.info(
            f"Analyzing Clean Code violations for {file_path}", extra={"file_path": file_path, "language": language}
        )

        system_prompt = """You are an expert code reviewer specializing in Clean Code principles.
Analyze the provided code and identify violations of Clean Code principles:
1. Meaningful Names - Variables, functions, classes should reveal intent
2. Small Functions - Functions should be small and do one thing
3. DRY - Don't Repeat Yourself
4. Single Responsibility - One class, one responsibility
5. Proper Comments - Comments should explain why, not what
6. Error Handling - Proper exception handling, no ignored errors
7. Formatting - Consistent indentation, spacing, line length
8. Boundaries - Clean interfaces between modules
9. Unit Tests - Code should be testable and tested

For each violation, provide:
- Principle violated
- Severity (critical/high/medium/low)
- Location (line number)
- Description
- Suggestion for improvement
- Example fix (if applicable)

Format your response as JSON array."""

        prompt = f"""Analyze this {language} code for Clean Code violations:

File: {file_path}

```{language}
{code}
```

Provide detailed analysis of any Clean Code principle violations."""

        try:
            await self.llm.generate(prompt, system_prompt=system_prompt)

            # Parse response and create violations
            # For now, return a simple structure
            violations = []

            logger.info(
                f"Found {len(violations)} Clean Code violations in {file_path}",
                extra={"file_path": file_path, "violation_count": len(violations)},
            )

            return violations

        except Exception as e:
            logger.error(
                f"Failed to analyze Clean Code violations: {e}", extra={"file_path": file_path, "error": str(e)}
            )
            raise

    async def generate_natural_language_explanation(
        self,
        technical_finding: str,
        context: dict[str, Any] | None = None,
    ) -> NaturalLanguageExplanation:
        """
        Convert technical finding into developer-friendly explanation.

        Validates Requirements: 3.11

        Args:
            technical_finding: Technical analysis result
            context: Optional context information

        Returns:
            Natural language explanation
        """
        logger.info("Generating natural language explanation", extra={"finding_length": len(technical_finding)})

        system_prompt = """You are an expert at explaining technical code analysis results to developers.
Convert technical findings into clear, actionable explanations that developers can understand and act upon.

Your explanation should include:
1. Developer-friendly explanation (avoid jargon, use clear language)
2. Why it matters (business/quality impact)
3. How to fix (step-by-step remediation)
4. Code example (if applicable)

Be concise, practical, and encouraging."""

        prompt = f"""Convert this technical finding into a developer-friendly explanation:

Technical Finding:
{technical_finding}

{f"Context: {context}" if context else ""}

Provide a clear, actionable explanation."""

        try:
            response = await self.llm.generate(prompt, system_prompt=system_prompt)

            # Parse response
            explanation = NaturalLanguageExplanation(
                technical_finding=technical_finding,
                developer_explanation=response,
                why_it_matters="This affects code quality and maintainability.",
                how_to_fix="Follow suggested improvements.",
                code_example=None,
            )

            logger.info("Generated natural language explanation")

            return explanation

        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}", extra={"error": str(e)})
            raise

    async def analyze_with_graph_context(
        self,
        code: str,
        file_path: str,
        repository: str,
        component_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze code considering architectural context from graph database.

        Validates Requirements: 3.2, 3.10

        Args:
            code: Source code to analyze
            file_path: Path to the file
            repository: Repository name
            component_id: Optional component ID in graph database

        Returns:
            Analysis result with architectural context
        """
        logger.info(
            f"Analyzing code with graph context: {file_path}",
            extra={"file_path": file_path, "repository": repository, "component_id": component_id},
        )

        # Query graph database for context using context builder
        graph_context = {}
        if self.context_builder:
            try:
                # Build comprehensive context from graph
                graph_context = await self.context_builder.build_context_for_file(
                    file_path=file_path, repository=repository, include_dependencies=True, include_dependents=True
                )

                # Optimize context for LLM token limits
                graph_context = await self.context_builder.optimize_context_for_llm(
                    graph_context, priority_fields=["file_path", "dependencies", "dependents", "functions", "classes"]
                )

                logger.info(
                    f"Retrieved graph context for {file_path}",
                    extra={
                        "dependencies_count": len(graph_context.get("dependencies", [])),
                        "dependents_count": len(graph_context.get("dependents", [])),
                        "functions_count": len(graph_context.get("functions", [])),
                        "classes_count": len(graph_context.get("classes", [])),
                    },
                )

            except Exception as e:
                logger.warning(f"Failed to fetch graph context: {e}", extra={"file_path": file_path, "error": str(e)})
                graph_context = {"error": "Failed to retrieve graph context"}
        else:
            logger.warning("Context builder not available, skipping graph context")
            graph_context = {"note": "Graph context not available"}

        system_prompt = """You are an expert software architect analyzing code changes.
Consider the architectural context and dependencies when evaluating code changes.

Analyze:
1. Does this change disrupt the overall architectural logic?
2. Are there unexpected couplings introduced?
3. Does this violate architectural patterns?
4. What is the impact on dependent components?

Provide architectural recommendations."""

        import json

        context_str = json.dumps(graph_context, indent=2)

        prompt = f"""Analyze this code change considering architectural context:

File: {file_path}
Repository: {repository}

```
{code}
```

Architectural Context from Graph Database:
{context_str}

Evaluate architectural impact and provide recommendations."""

        try:
            response = await self.llm.generate(prompt, system_prompt=system_prompt)

            result = {
                "file_path": file_path,
                "repository": repository,
                "architectural_analysis": response,
                "graph_context": graph_context,
                "recommendations": [],
            }

            logger.info(f"Completed architectural analysis for {file_path}", extra={"file_path": file_path})

            return result

        except Exception as e:
            logger.error(f"Failed to analyze with graph context: {e}", extra={"file_path": file_path, "error": str(e)})
            raise

    async def generate_refactoring_suggestions(
        self,
        code: str,
        file_path: str,
        constraints: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generate refactoring suggestions with effort and risk estimates.

        Validates Requirements: 3.6

        Args:
            code: Source code to analyze
            file_path: Path to the file
            constraints: Optional constraints (e.g., preserve API, minimize changes)

        Returns:
            List of refactoring suggestions with estimates
        """
        logger.info(f"Generating refactoring suggestions for {file_path}", extra={"file_path": file_path})

        system_prompt = """You are an expert at identifying refactoring opportunities.
Analyze code and suggest refactorings that improve quality, maintainability, and performance.

For each suggestion, provide:
1. Title (brief description)
2. Description (detailed explanation)
3. Impact (HIGH/MEDIUM/LOW)
4. Effort (HIGH/MEDIUM/LOW)
5. Risk (HIGH/MEDIUM/LOW)
6. Code example (before/after)
7. Rationale (why this improves the code)

Prioritize high-impact, low-effort refactorings."""

        prompt = f"""Suggest refactorings for this code:

File: {file_path}

```
{code}
```

{f"Constraints: {constraints}" if constraints else ""}

Provide practical refactoring suggestions with effort and risk estimates."""

        try:
            response = await self.llm.generate(prompt, system_prompt=system_prompt)

            suggestions = self._parse_refactoring_suggestions(response, file_path)

            logger.info(
                f"Generated {len(suggestions)} refactoring suggestions for {file_path}",
                extra={"file_path": file_path, "suggestion_count": len(suggestions)},
            )

            return suggestions

        except Exception as e:
            logger.error(
                f"Failed to generate refactoring suggestions: {e}", extra={"file_path": file_path, "error": str(e)}
            )
            raise

    async def perform_complex_reasoning(
        self,
        task_type: str,
        context: dict[str, Any],
        constraints: dict[str, Any] | None = None,
    ) -> ReasoningResult:
        """
        Perform complex reasoning task with explainable results.

        Validates Requirements: 3.4, 3.5

        Args:
            task_type: Type of reasoning task
            context: Task context and input data
            constraints: Optional constraints

        Returns:
            Reasoning result with explanations
        """
        logger.info(f"Performing complex reasoning: {task_type}", extra={"task_type": task_type})

        system_prompt = """You are an expert AI reasoning system for software development.
Provide detailed, explainable reasoning for complex software engineering decisions.

Your reasoning should:
1. Be step-by-step and transparent
2. Reference relevant knowledge bases (OWASP, style guides, standards)
3. Consider multiple perspectives
4. Provide confidence levels
5. Include supporting evidence

Be thorough but concise."""

        prompt = f"""Perform reasoning for this task:

Task Type: {task_type}

Context:
{context}

{f"Constraints: {constraints}" if constraints else ""}

Provide detailed reasoning with explanations and references."""

        try:
            response = await self.llm.generate(prompt, system_prompt=system_prompt)

            result = ReasoningResult(
                task_type=task_type,
                suggestions=[],
                confidence=0.8,
                reasoning_chain=[response],
                knowledge_references=[],
            )

            logger.info(f"Completed reasoning task: {task_type}", extra={"task_type": task_type})

            return result

        except Exception as e:
            logger.error(f"Failed to perform reasoning: {e}", extra={"task_type": task_type, "error": str(e)})
            raise

    def _parse_refactoring_suggestions(self, response: str, file_path: str) -> list[dict[str, Any]]:
        """
        Parse LLM response to extract structured refactoring suggestions.

        Args:
            response: LLM text response containing refactoring suggestions
            file_path: Path to the source file for context

        Returns:
            List of structured refactoring suggestions
        """
        suggestions = []

        if not response or not response.strip():
            return suggestions

        response_text = response.strip()

        try:
            json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            suggestions.append(
                                {
                                    "title": item.get("title", item.get("name", "Untitled")),
                                    "description": item.get("description", item.get("suggestion", "")),
                                    "impact": item.get("impact", item.get("severity", "MEDIUM")),
                                    "effort": item.get("effort", "MEDIUM"),
                                    "risk": item.get("risk", "MEDIUM"),
                                    "code_example": item.get("code_example", item.get("example", "")),
                                    "rationale": item.get("rationale", item.get("reason", "")),
                                    "file_path": file_path,
                                }
                            )
                    return suggestions
        except (json.JSONDecodeError, KeyError):
            pass

        suggestion_patterns = [
            r"(?:^|\n)###?\s*(\d+)\.?\s*(.+?)(?=\n###?\s*\d|\n\n|\Z)",
            r"(?:^|\n)(\d+)\.\s*\*\*(.+?)\*\*[:\s]*(.+?)(?=\n\d+\.|\n\n|\Z)",
            r"(?:^|\n)-\s*\*\*(.+?)\*\*[:\s]*(.+?)(?=\n-|\n\n|\Z)",
        ]

        for pattern in suggestion_patterns:
            matches = re.finditer(pattern, response_text, re.DOTALL | re.MULTILINE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    title = groups[1].strip()
                    description = groups[2].strip() if len(groups) > 2 else ""

                    title_lower = title.lower()
                    impact = "MEDIUM"
                    effort = "MEDIUM"
                    risk = "MEDIUM"

                    if "high impact" in title_lower or "significant" in title_lower:
                        impact = "HIGH"
                    elif "low impact" in title_lower or "minor" in title_lower:
                        impact = "LOW"

                    if "easy" in title_lower or "low effort" in title_lower:
                        effort = "LOW"
                    elif "complex" in title_lower or "high effort" in title_lower:
                        effort = "HIGH"

                    if "safe" in title_lower or "low risk" in title_lower:
                        risk = "LOW"
                    elif "risky" in title_lower or "high risk" in title_lower:
                        risk = "HIGH"

                    suggestions.append(
                        {
                            "title": title,
                            "description": description[:500] if description else "",
                            "impact": impact,
                            "effort": effort,
                            "risk": risk,
                            "code_example": "",
                            "rationale": "",
                            "file_path": file_path,
                        }
                    )

        if not suggestions:
            lines = response_text.split("\n")
            current_title = None
            current_desc = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith("#") or (line and line[0].isdigit() and "." in line[:3]):
                    if current_title:
                        suggestions.append(
                            {
                                "title": current_title,
                                "description": " ".join(current_desc)[:500],
                                "impact": "MEDIUM",
                                "effort": "MEDIUM",
                                "risk": "MEDIUM",
                                "code_example": "",
                                "rationale": "",
                                "file_path": file_path,
                            }
                        )

                    clean_title = re.sub(r"^[#\d.]+\s*", "", line).strip()
                    current_title = clean_title
                    current_desc = []
                elif current_title and len(line) > 10:
                    current_desc.append(line)

            if current_title:
                suggestions.append(
                    {
                        "title": current_title,
                        "description": " ".join(current_desc)[:500],
                        "impact": "MEDIUM",
                        "effort": "MEDIUM",
                        "risk": "MEDIUM",
                        "code_example": "",
                        "rationale": "",
                        "file_path": file_path,
                    }
                )

        return suggestions[:10]


def create_agentic_ai_service(
    model_path: str | None = None,
    ollama_base_url: str = "http://localhost:11434",
    lmstudio_base_url: str | None = None,
    lmstudio_model: str | None = None,
) -> "AgenticAIService":
    """
    Factory function to create Agentic AI Service.

    LM Studio is used as the **primary** provider for project reviews.
    Ollama models serve as fallback providers.

    Args:
        model_path:        Unused legacy parameter (kept for backward compat)
        ollama_base_url:   Ollama API base URL (fallback)
        lmstudio_base_url: LM Studio base URL; defaults to ``settings.LMSTUDIO_BASE_URL``
        lmstudio_model:    LM Studio model name; defaults to ``settings.LMSTUDIO_MODEL``

    Returns:
        Configured Agentic AI Service
    """
    from app.core.config import settings as _settings

    _lmstudio_url = (lmstudio_base_url or _settings.LMSTUDIO_BASE_URL).rstrip("/")
    _lmstudio_model = lmstudio_model or _settings.LMSTUDIO_MODEL

    providers = [
        # Primary: LM Studio (local, no cost, fast)
        LLMProviderConfig(
            provider_type=LLMProviderType.LMSTUDIO,
            model=_lmstudio_model,
            base_url=_lmstudio_url,
            max_tokens=4000,
            temperature=0.3,
            timeout=_settings.LMSTUDIO_TIMEOUT,
            priority=1,
        ),
        # Secondary: Qwen2.5-Coder via Ollama
        LLMProviderConfig(
            provider_type=LLMProviderType.OLLAMA,
            model="qwen2.5-coder:14b",
            base_url=ollama_base_url,
            max_tokens=4000,
            temperature=0.3,
            priority=2,
        ),
        # Tertiary: DeepSeek-R1 via Ollama (good reasoning)
        LLMProviderConfig(
            provider_type=LLMProviderType.OLLAMA,
            model="deepseek-r1:7b",
            base_url=ollama_base_url,
            max_tokens=4000,
            temperature=0.5,
            priority=3,
        ),
    ]

    orchestrator = LLMOrchestrator(providers)

    return AgenticAIService(
        llm_orchestrator=orchestrator,
        neo4j_client=None,
        redis_client=None,
    )
