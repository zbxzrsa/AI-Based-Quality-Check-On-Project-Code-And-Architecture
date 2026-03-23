"""
DeepSeek AI Service for Code Review

Integrates with the DeepSeek API to perform AI-powered code review analysis.
Provides code quality assessment, security analysis, and architectural feedback.
"""
import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeepSeekReviewResult:
    """Result from DeepSeek AI code review."""
    safety_score: int = 85  # 0-100
    summary: str = ""
    architectural_issues: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    code_quality_issues: List[str] = field(default_factory=list)
    refactoring_suggestions: List[str] = field(default_factory=list)
    architecture_diagram: Optional[str] = None  # Mermaid diagram


class DeepSeekService:
    """
    DeepSeek AI service for code review and architecture analysis.
    
    Supports:
    - PR diff analysis with quality scoring
    - Architecture diagram generation from code
    - Code pattern detection and recommendations
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_available(self) -> bool:
        """Check if DeepSeek API is configured."""
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def _chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """Call DeepSeek chat completion API."""
        if not self.is_available:
            raise ValueError("DeepSeek API key not configured")

        client = await self._get_client()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
            "stream": False,
        }

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API error: {e.response.status_code} - {e.response.text[:200]}")
            raise
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            raise

    async def review_code_diff(
        self,
        diff_content: str,
        pr_title: str = "",
        pr_description: str = "",
        language_hint: str = "",
    ) -> DeepSeekReviewResult:
        """
        Review a code diff using DeepSeek AI.

        Args:
            diff_content: The git diff content
            pr_title: PR title for context
            pr_description: PR description for context
            language_hint: Hint about the programming language

        Returns:
            DeepSeekReviewResult with AI analysis
        """
        if not self.is_available:
            logger.warning("DeepSeek API not configured, using rule-based fallback")
            return self._rule_based_review(diff_content)

        system_prompt = """你是一位资深的代码审查专家。请对以下代码变更进行全面审查。

请以以下 JSON 格式返回审查结果（只返回 JSON，不要其他文字）：
{
    "safety_score": <0-100的整数>,
    "summary": "<简要总结>",
    "architectural_issues": ["<架构问题1>", ...],
    "security_issues": ["<安全问题1>", ...],
    "code_quality_issues": ["<代码质量问题1>", ...],
    "refactoring_suggestions": ["<重构建议1>", ...]
}

评分标准:
- 85-100: 合规，代码质量优秀
- 60-84: 警告，存在需要关注的问题
- 0-59: 违规，存在严重问题需要修复

审查重点:
1. 架构问题: 分层违规、循环依赖、职责不清
2. 安全问题: SQL注入、XSS、硬编码密钥、输入未校验
3. 代码质量: 过长函数、深层嵌套、魔法数字、缺少错误处理
4. 重构建议: 可优化的代码模式"""

        user_content = f"""PR 标题: {pr_title}
PR 描述: {pr_description}
编程语言: {language_hint or '自动检测'}

代码变更 (Git Diff):
```diff
{diff_content[:8000]}
```"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response_text = await self._chat_completion(messages)
            return self._parse_review_response(response_text)
        except Exception as e:
            logger.error(f"DeepSeek review failed, falling back to rules: {e}")
            return self._rule_based_review(diff_content)

    async def generate_architecture_diagram(
        self,
        code_files: List[Dict[str, str]],
        review_summary: Optional[str] = None,
    ) -> str:
        """
        Generate a Mermaid architecture diagram from code analysis.

        Args:
            code_files: List of dicts with 'filename' and 'content' (or 'patch')
            review_summary: Optional summary from a code review

        Returns:
            Mermaid diagram definition string
        """
        if not self.is_available:
            return self._rule_based_architecture_diagram(code_files)

        # Build file list for context
        file_info = "\n".join(
            f"- {f.get('filename', 'unknown')}" +
            (f" (变更: {f.get('patch', '')[:200]}...)" if f.get('patch') else "")
            for f in code_files[:30]  # Limit to 30 files
        )

        system_prompt = """你是一位软件架构师。请根据提供的代码文件信息生成一个 Mermaid 架构图。

要求：
1. 只返回 Mermaid 图表代码，不要其他文字
2. 使用 flowchart TD（自上而下流程图）格式
3. 按分层架构组织：前端 → API层 → 服务层 → 数据层
4. 用 subgraph 分组相关模块
5. 用不同样式标注不同类型的组件
6. 如果发现架构问题（如循环依赖），用红色标注

示例格式:
```mermaid
flowchart TD
    subgraph Frontend["🖥️ 前端层"]
        A[页面组件]
        B[状态管理]
    end
    subgraph API["🔌 API 层"]
        C[路由控制器]
        D[中间件]
    end
    subgraph Service["⚙️ 服务层"]
        E[业务逻辑]
        F[外部集成]
    end
    subgraph Data["💾 数据层"]
        G[(数据库)]
        H[(缓存)]
    end
    A --> C
    C --> D --> E
    E --> G
    E --> H
    B --> C
    E --> F
```"""

        user_content = f"""项目文件列表:
{file_info}"""

        if review_summary:
            user_content += f"\n\n代码审查摘要:\n{review_summary}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response_text = await self._chat_completion(messages, temperature=0.2)
            # Extract mermaid code block if wrapped
            diagram = self._extract_mermaid(response_text)
            return diagram
        except Exception as e:
            logger.error(f"DeepSeek diagram generation failed: {e}")
            return self._rule_based_architecture_diagram(code_files)

    def _parse_review_response(self, response_text: str) -> DeepSeekReviewResult:
        """Parse AI response into structured review result."""
        try:
            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                data = json.loads(response_text[json_start:json_end])
                return DeepSeekReviewResult(
                    safety_score=min(100, max(0, int(data.get("safety_score", 85)))),
                    summary=data.get("summary", ""),
                    architectural_issues=data.get("architectural_issues", []),
                    security_issues=data.get("security_issues", []),
                    code_quality_issues=data.get("code_quality_issues", []),
                    refactoring_suggestions=data.get("refactoring_suggestions", []),
                )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse DeepSeek response as JSON: {e}")

        # Fallback: return the raw text as summary
        return DeepSeekReviewResult(
            safety_score=75,
            summary=response_text[:500],
        )

    def _extract_mermaid(self, text: str) -> str:
        """Extract Mermaid diagram from response text."""
        # Look for ```mermaid ... ``` block
        if "```mermaid" in text:
            start = text.index("```mermaid") + len("```mermaid")
            end = text.index("```", start)
            return text[start:end].strip()
        # Look for ```  ... ``` block that starts with flowchart/graph
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                stripped = part.strip()
                if stripped.startswith(("flowchart", "graph", "classDiagram", "sequenceDiagram")):
                    return stripped
        # Return as-is if no code block found
        return text.strip()

    def _rule_based_review(self, diff_content: str) -> DeepSeekReviewResult:
        """Fallback rule-based review when API is unavailable."""
        issues_security = []
        issues_quality = []
        issues_arch = []
        suggestions = []

        lines = diff_content.split("\n")
        added_lines = [l for l in lines if l.startswith("+") and not l.startswith("+++")]

        for line in added_lines:
            lower = line.lower()
            # Security checks
            if any(kw in lower for kw in ["password", "secret", "api_key", "token"]):
                if any(kw in lower for kw in ["= \"", "= '", "='", "=\""]):
                    issues_security.append(f"可能存在硬编码的敏感信息: {line[:80].strip()}")
            if "eval(" in lower or "exec(" in lower:
                issues_security.append(f"使用了危险的动态执行: {line[:80].strip()}")
            if "sql" in lower and ("format" in lower or "%" in lower or "f'" in lower or 'f"' in lower):
                issues_security.append(f"可能存在 SQL 注入风险: {line[:80].strip()}")

            # Code quality checks
            if len(line) > 120:
                issues_quality.append("代码行过长 (>120字符)，建议拆分")
            if "todo" in lower or "fixme" in lower or "hack" in lower:
                issues_quality.append(f"遗留标记: {line[:80].strip()}")
            if "except:" in line and "pass" in line:
                issues_quality.append("吞没异常 (except: pass)，不利于调试")

        # Architecture checks
        if any("import" in l and "database" in l.lower() for l in added_lines if l.startswith("+")):
            if any("component" in l.lower() or "view" in l.lower() or "page" in l.lower() for l in added_lines):
                issues_arch.append("UI 组件直接访问数据库层，违反分层架构")

        # Calculate score
        base_score = 100
        base_score -= len(issues_security) * 20
        base_score -= len(issues_quality) * 5
        base_score -= len(issues_arch) * 15

        if not issues_security and not issues_quality and not issues_arch:
            suggestions.append("代码变更看起来良好，未发现明显问题")

        return DeepSeekReviewResult(
            safety_score=max(0, min(100, base_score)),
            summary=f"规则引擎审查完成: {len(issues_security)} 安全问题, {len(issues_quality)} 质量问题, {len(issues_arch)} 架构问题",
            architectural_issues=issues_arch,
            security_issues=issues_security,
            code_quality_issues=issues_quality,
            refactoring_suggestions=suggestions,
        )

    def _rule_based_architecture_diagram(self, code_files: List[Dict[str, str]]) -> str:
        """Generate a basic architecture diagram from file structure."""
        # Categorize files by their paths
        categories = {
            "frontend": [],
            "api": [],
            "service": [],
            "database": [],
            "config": [],
            "other": [],
        }

        for f in code_files:
            name = f.get("filename", "").lower()
            if any(kw in name for kw in ["component", "page", "view", "tsx", "jsx", "css", "html"]):
                categories["frontend"].append(f.get("filename", ""))
            elif any(kw in name for kw in ["route", "endpoint", "controller", "api"]):
                categories["api"].append(f.get("filename", ""))
            elif any(kw in name for kw in ["service", "handler", "logic", "util"]):
                categories["service"].append(f.get("filename", ""))
            elif any(kw in name for kw in ["model", "schema", "migration", "database", "db"]):
                categories["database"].append(f.get("filename", ""))
            elif any(kw in name for kw in ["config", "setting", "env"]):
                categories["config"].append(f.get("filename", ""))
            else:
                categories["other"].append(f.get("filename", ""))

        # Build Mermaid diagram
        diagram = "flowchart TD\n"
        
        if categories["frontend"]:
            diagram += '    subgraph Frontend["🖥️ 前端层"]\n'
            for i, f in enumerate(categories["frontend"][:5]):
                diagram += f'        FE{i}["{self._short_name(f)}"]\n'
            diagram += "    end\n"

        if categories["api"]:
            diagram += '    subgraph API["🔌 API 层"]\n'
            for i, f in enumerate(categories["api"][:5]):
                diagram += f'        API{i}["{self._short_name(f)}"]\n'
            diagram += "    end\n"

        if categories["service"]:
            diagram += '    subgraph Service["⚙️ 服务层"]\n'
            for i, f in enumerate(categories["service"][:5]):
                diagram += f'        SVC{i}["{self._short_name(f)}"]\n'
            diagram += "    end\n"

        if categories["database"]:
            diagram += '    subgraph Data["💾 数据层"]\n'
            for i, f in enumerate(categories["database"][:5]):
                diagram += f'        DB{i}[("{self._short_name(f)}")]\n'
            diagram += "    end\n"

        # Add connections
        if categories["frontend"] and categories["api"]:
            diagram += "    Frontend --> API\n"
        if categories["api"] and categories["service"]:
            diagram += "    API --> Service\n"
        if categories["service"] and categories["database"]:
            diagram += "    Service --> Data\n"
        if categories["frontend"] and not categories["api"] and categories["service"]:
            diagram += "    Frontend --> Service\n"

        return diagram

    @staticmethod
    def _short_name(filepath: str) -> str:
        """Get short display name from filepath."""
        parts = filepath.replace("\\", "/").split("/")
        return parts[-1] if parts else filepath


# Singleton instance management
_deepseek_instance: Optional[DeepSeekService] = None


def get_deepseek_service() -> DeepSeekService:
    """Get or create the global DeepSeek service instance."""
    global _deepseek_instance
    if _deepseek_instance is None:
        from app.core.config import settings
        _deepseek_instance = DeepSeekService(
            api_key=getattr(settings, "DEEPSEEK_API_KEY", None),
            base_url=getattr(settings, "DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=getattr(settings, "DEEPSEEK_MODEL", "deepseek-chat"),
        )
    return _deepseek_instance


async def close_deepseek_service():
    """Close the DeepSeek service client."""
    global _deepseek_instance
    if _deepseek_instance and _deepseek_instance._client:
        await _deepseek_instance._client.aclose()
        _deepseek_instance = None
