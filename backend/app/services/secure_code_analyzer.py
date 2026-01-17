"""
Secure Code Analysis Service
Provides hardened code analysis without execution risks
"""
import ast
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisRisk(Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityIssue:
    def __init__(self, issue_type: str, severity: AnalysisRisk, location: str,
                 description: str, code_snippet: str = "", suggestion: str = ""):
        self.issue_type = issue_type
        self.severity = severity
        self.location = location
        self.description = description
        self.code_snippet = code_snippet
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity.value,
            "location": self.location,
            "description": self.description,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion
        }


@dataclass
class AnalysisResult:
    issues: List[SecurityIssue]
    complexity_score: int
    analysis_type: str = "static_ast"
    analysis_time: float = 0.0
    total_lines: int = 0
    functions_count: int = 0
    classes_count: int = 0


class SecureASTVisitor(ast.NodeVisitor):
    """
    Secure AST visitor that analyzes code structure without execution
    """

    def __init__(self, filename: str = "<string>"):
        self.filename = filename
        self.issues: List[SecurityIssue] = []
        self.complexity_score = 0
        self.function_count = 0
        self.class_count = 0
        self.current_function: Optional[str] = None
        self.nesting_level = 0
        self.max_nesting = 0

        # Security patterns to detect
        self.dangerous_functions = {
            'eval', 'exec', 'compile', '__import__', 'open', 'input',
            'subprocess.call', 'subprocess.run', 'subprocess.Popen',
            'os.system', 'os.popen', 'pickle.loads', 'pickle.load',
            'yaml.load', 'yaml.unsafe_load'
        }

        self.dangerous_imports = {
            'subprocess', 'pickle', 'os', 'sys', 'shutil'
        }

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze function definitions"""
        self.function_count += 1
        old_function = self.current_function
        self.current_function = node.name

        # Check function complexity
        complexity = self._calculate_function_complexity(node)
        self.complexity_score += complexity

        if complexity > 10:
            self.issues.append(SecurityIssue(
                issue_type="high_complexity",
                severity=AnalysisRisk.MEDIUM,
                location=f"{self.filename}:{node.lineno}",
                description=f"Function '{node.name}' has high complexity ({complexity})",
                suggestion="Consider breaking down into smaller functions"
            ))

        # Check function name security
        if self._is_suspicious_function_name(node.name):
            self.issues.append(SecurityIssue(
                issue_type="suspicious_function_name",
                severity=AnalysisRisk.MEDIUM,
                location=f"{self.filename}:{node.lineno}",
                description=f"Suspicious function name: {node.name}",
                suggestion="Review function purpose and naming"
            ))

        self.generic_visit(node)
        self.current_function = old_function

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Analyze class definitions"""
        self.class_count += 1

        # Check class design
        if len(node.body) > 20:
            self.issues.append(SecurityIssue(
                issue_type="large_class",
                severity=AnalysisRisk.LOW,
                location=f"{self.filename}:{node.lineno}",
                description=f"Class '{node.name}' is very large ({len(node.body)} members)",
                suggestion="Consider splitting into smaller classes"
            ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Analyze function calls for security issues"""
        func_name = self._get_full_function_name(node.func)

        if func_name in self.dangerous_functions:
            severity = AnalysisRisk.CRITICAL if 'eval' in func_name or 'exec' in func_name else AnalysisRisk.HIGH
            self.issues.append(SecurityIssue(
                issue_type="dangerous_function_call",
                severity=severity,
                location=f"{self.filename}:{node.lineno}",
                description=f"Call to dangerous function: {func_name}",
                code_snippet=self._get_source_code(node),
                suggestion=self._get_security_suggestion(func_name)
            ))

        # Check for SQL injection patterns
        if self._is_sql_injection_risk(node):
            self.issues.append(SecurityIssue(
                issue_type="sql_injection_risk",
                severity=AnalysisRisk.HIGH,
                location=f"{self.filename}:{node.lineno}",
                description="Potential SQL injection vulnerability",
                code_snippet=self._get_source_code(node),
                suggestion="Use parameterized queries or ORM"
            ))

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Analyze import statements"""
        for alias in node.names:
            if alias.name in self.dangerous_imports:
                self.issues.append(SecurityIssue(
                    issue_type="dangerous_import",
                    severity=AnalysisRisk.MEDIUM,
                    location=f"{self.filename}:{node.lineno}",
                    description=f"Import of potentially dangerous module: {alias.name}",
                    suggestion="Review if this import is necessary"
                ))

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Analyze from-import statements"""
        if node.module in self.dangerous_imports:
            self.issues.append(SecurityIssue(
                issue_type="dangerous_import",
                severity=AnalysisRisk.MEDIUM,
                location=f"{self.filename}:{node.lineno}",
                description=f"Import from potentially dangerous module: {node.module}",
                suggestion="Review if this import is necessary"
            ))

        self.generic_visit(node)

    def visit_Str(self, node: ast.Str) -> None:
        """Analyze string literals for hardcoded secrets"""
        if self._contains_hardcoded_secret(node.s):
            self.issues.append(SecurityIssue(
                issue_type="hardcoded_secret",
                severity=AnalysisRisk.HIGH,
                location=f"{self.filename}:{node.lineno}",
                description="Potential hardcoded secret detected",
                code_snippet=f'"{node.s[:20]}..."',
                suggestion="Use environment variables or secure key management"
            ))

    def visit_If(self, node: ast.If) -> None:
        """Track nesting levels"""
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)

        if self.nesting_level > 5:
            self.issues.append(SecurityIssue(
                issue_type="deep_nesting",
                severity=AnalysisRisk.LOW,
                location=f"{self.filename}:{node.lineno}",
                description=f"Deep nesting level ({self.nesting_level})",
                suggestion="Consider refactoring to reduce nesting"
            ))

        self.generic_visit(node)
        self.nesting_level -= 1

    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp) and len(child.values) > 1:
                complexity += len(child.values) - 1

        return complexity

    def _get_full_function_name(self, node: ast.AST) -> str:
        """Get the full function name from an AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_full_function_name(node.value)}.{node.attr}"
        return str(node)

    def _is_sql_injection_risk(self, node: ast.Call) -> bool:
        """Check if a function call has SQL injection risk"""
        func_name = self._get_full_function_name(node.func)

        # Common SQL execution patterns
        sql_patterns = ['execute', 'executemany', 'cursor.execute']
        if any(pattern in func_name for pattern in sql_patterns):
            # Check if using string formatting instead of parameters
            if len(node.args) >= 2:
                sql_arg = node.args[0]
                if isinstance(sql_arg, ast.Str) and ('%' in sql_arg.s or '+' in sql_arg.s):
                    return True

        return False

    def _contains_hardcoded_secret(self, text: str) -> bool:
        """Check if a string contains potential hardcoded secrets"""
        secret_indicators = [
            'password', 'secret', 'key', 'token', 'api_key',
            'sk-', 'pk-', 'Bearer ', 'Authorization:'
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in secret_indicators)

    def _is_suspicious_function_name(self, name: str) -> bool:
        """Check if function name suggests suspicious behavior"""
        suspicious_patterns = [
            'inject', 'exploit', 'hack', 'bypass', 'override',
            'unsafe', 'dangerous', 'evil'
        ]

        name_lower = name.lower()
        return any(pattern in name_lower for pattern in suspicious_patterns)

    def _get_source_code(self, node: ast.AST) -> str:
        """Get source code representation of an AST node"""
        try:
            return ast.get_source_segment(self.source_code, node) or str(node)
        except:
            return str(node)

    def _get_security_suggestion(self, func_name: str) -> str:
        """Get security suggestion for dangerous function"""
        suggestions = {
            'eval': 'Use ast.literal_eval() for safe evaluation, or avoid completely',
            'exec': 'Avoid exec() - use import or other safe alternatives',
            'pickle.loads': 'Use pickle.loads() only with trusted data',
            'subprocess.call': 'Use subprocess.run() with shell=False',
            'os.system': 'Use subprocess.run() instead'
        }
        return suggestions.get(func_name, f"Avoid using {func_name} if possible")


class SecureCodeAnalyzer:
    """
    Main secure code analyzer class
    """

    def __init__(self, timeout_seconds: int = 30, max_file_size: int = 1024 * 1024):
        self.timeout_seconds = timeout_seconds
        self.max_file_size = max_file_size

    def analyze_code(self, source_code: str, filename: str = "<string>") -> AnalysisResult:
        """
        Analyze source code securely using AST parsing

        Args:
            source_code: The source code to analyze
            filename: Name of the file being analyzed

        Returns:
            AnalysisResult with security issues and metrics
        """
        import time
        start_time = time.time()

        # Input validation
        if len(source_code) > self.max_file_size:
            raise ValueError(f"File size exceeds maximum limit of {self.max_file_size} bytes")

        if not source_code.strip():
            return AnalysisResult([], 0, "empty_file")

        try:
            # Parse AST safely
            tree = ast.parse(source_code, filename=filename)

            # Create visitor and analyze
            visitor = SecureASTVisitor(filename)
            visitor.source_code = source_code  # For source code extraction
            visitor.visit(tree)

            # Calculate analysis time
            analysis_time = time.time() - start_time

            # Create result
            result = AnalysisResult(
                issues=visitor.issues,
                complexity_score=visitor.complexity_score,
                analysis_type="static_ast",
                analysis_time=analysis_time,
                total_lines=len(source_code.splitlines()),
                functions_count=visitor.function_count,
                classes_count=visitor.class_count
            )

            logger.info(f"Analysis completed for {filename}: {len(result.issues)} issues found")
            return result

        except SyntaxError as e:
            # Handle syntax errors gracefully
            issue = SecurityIssue(
                issue_type="syntax_error",
                severity=AnalysisRisk.LOW,
                location=f"{filename}:{e.lineno or 0}",
                description=f"Syntax error: {e.msg}",
                suggestion="Fix syntax error before analysis"
            )
            return AnalysisResult([issue], 0, "syntax_error", time.time() - start_time)

        except Exception as e:
            logger.error(f"Analysis failed for {filename}: {str(e)}")
            issue = SecurityIssue(
                issue_type="analysis_error",
                severity=AnalysisRisk.LOW,
                location=filename,
                description=f"Analysis failed: {str(e)}",
                suggestion="Check file format and try again"
            )
            return AnalysisResult([issue], 0, "error", time.time() - start_time)

    def analyze_multiple_files(self, files: Dict[str, str]) -> Dict[str, AnalysisResult]:
        """
        Analyze multiple files securely

        Args:
            files: Dictionary mapping filenames to source code

        Returns:
            Dictionary mapping filenames to analysis results
        """
        results = {}

        for filename, source_code in files.items():
            try:
                results[filename] = self.analyze_code(source_code, filename)
            except Exception as e:
                logger.error(f"Failed to analyze {filename}: {str(e)}")
                # Return error result
                error_issue = SecurityIssue(
                    issue_type="file_error",
                    severity=AnalysisRisk.LOW,
                    location=filename,
                    description=f"Could not analyze file: {str(e)}"
                )
                results[filename] = AnalysisResult([error_issue], 0, "error")

        return results

    def get_summary_report(self, results: Dict[str, AnalysisResult]) -> Dict[str, Any]:
        """Generate a summary report from multiple analysis results"""
        total_files = len(results)
        total_issues = sum(len(result.issues) for result in results.values())
        total_complexity = sum(result.complexity_score for result in results.values())

        severity_counts = {
            AnalysisRisk.CRITICAL: 0,
            AnalysisRisk.HIGH: 0,
            AnalysisRisk.MEDIUM: 0,
            AnalysisRisk.LOW: 0
        }

        for result in results.values():
            for issue in result.issues:
                severity_counts[issue.severity] += 1

        return {
            "total_files": total_files,
            "total_issues": total_issues,
            "total_complexity": total_complexity,
            "severity_breakdown": {k.value: v for k, v in severity_counts.items()},
            "average_complexity": total_complexity / total_files if total_files > 0 else 0,
            "files_with_issues": sum(1 for r in results.values() if r.issues)
        }


# Example usage functions
def demonstrate_secure_analysis():
    """Demonstrate secure code analysis"""

    # Sample code with various issues
    test_code = '''
import os
import pickle
import subprocess

def dangerous_function():
    # High complexity function
    if True:
        if True:
            if True:
                if True:
                    if True:
                        if True:
                            # Dangerous calls
                            result = eval("1+1")  # CRITICAL
                            os.system("ls")      # HIGH
                            data = pickle.loads(b"bad")  # HIGH
                            subprocess.call(["rm", "-rf", "/"])  # CRITICAL

                            # SQL injection risk
                            cursor.execute("SELECT * FROM users WHERE id = " + user_id)

                            # Hardcoded secret
                            api_key = "sk-1234567890abcdef"

    return result

class LargeClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    # ... many more methods
'''

    analyzer = SecureCodeAnalyzer()
    result = analyzer.analyze_code(test_code, "test_file.py")

    print(f"Analysis completed in {result.analysis_time:.2f} seconds")
    print(f"Found {len(result.issues)} issues:")
    print(f"Complexity score: {result.complexity_score}")
    print(f"Functions: {result.functions_count}, Classes: {result.classes_count}")

    for issue in result.issues:
        print(f"[{issue.severity.value.upper()}] {issue.issue_type}: {issue.description}")
        if issue.suggestion:
            print(f"  Suggestion: {issue.suggestion}")
        print()


if __name__ == "__main__":
    demonstrate_secure_analysis()
