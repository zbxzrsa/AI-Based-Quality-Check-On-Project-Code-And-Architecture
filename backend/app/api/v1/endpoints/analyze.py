"""
Architecture Analysis API Endpoint

This module provides the /analyze endpoint for analyzing GitHub repositories
and extracting architectural information using AST parsing and AI analysis.
"""

import os
import tempfile
import shutil
import subprocess
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import git
import ast
import json
import re
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse
import aiofiles

from app.services.llm_client import LLMClient, LLMProvider
from app.services.neo4j_ast_service_extended import Neo4jASTService
from app.services.architecture_prompts import (
    format_architectural_purpose_prompt,
    format_architectural_patterns_prompt,
    format_code_quality_prompt
)
from app.core.logging_config import logger

router = APIRouter()

class AnalyzeRequest(BaseModel):
    repositoryUrl: str = Field(..., description="GitHub repository URL to analyze")
    includeArchitectureAnalysis: bool = Field(True, description="Include architecture analysis")
    includeComplexityMetrics: bool = Field(True, description="Include complexity metrics")
    includeDependencyAnalysis: bool = Field(True, description="Include dependency analysis")

class AnalysisResult(BaseModel):
    repositoryUrl: str
    analysisId: str
    status: str
    architectureSummary: Dict[str, Any]
    codeHierarchy: Dict[str, Any]
    metrics: Dict[str, Any]

class AnalysisProgress(BaseModel):
    stage: str
    progress: int
    message: str

class ArchitectureAnalyzer:
    """Service for analyzing repository architecture and code structure."""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.neo4j_service = Neo4jASTService()
        self.temp_dirs = []
    
    async def analyze_repository(self, request: AnalyzeRequest) -> Dict[str, Any]:
        """Main analysis orchestrator."""
        analysis_id = f"analysis_{hash(request.repositoryUrl)}_{hash(str(request))}"
        
        try:
            # Stage 1: Repository Cloning
            self._send_progress("cloning", 10, "Cloning repository...")
            repo_path = self._clone_repository(request.repositoryUrl)
            
            # Stage 2: Code Analysis
            self._send_progress("analyzing", 30, "Analyzing code structure...")
            code_hierarchy = self._analyze_code_structure(repo_path)
            
            # Stage 3: Complexity Metrics
            if request.includeComplexityMetrics:
                self._send_progress("metrics", 60, "Calculating complexity metrics...")
                metrics = self._calculate_complexity_metrics(code_hierarchy)
            else:
                metrics = {}
            
            # Stage 4: Architecture Analysis
            if request.includeArchitectureAnalysis:
                self._send_progress("architecture", 80, "Analyzing architectural patterns...")
                architecture_summary = self._analyze_architecture(code_hierarchy, metrics)
            else:
                architecture_summary = {}
            
            # Stage 5: Neo4j Integration
            self._send_progress("neo4j", 90, "Storing in Neo4j database...")
            self._store_in_neo4j(code_hierarchy, architecture_summary, metrics)
            
            # Stage 6: Completion
            self._send_progress("completed", 100, "Analysis complete!")
            
            result = {
                "repositoryUrl": request.repositoryUrl,
                "analysisId": analysis_id,
                "status": "completed",
                "architectureSummary": architecture_summary,
                "codeHierarchy": code_hierarchy,
                "metrics": metrics
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Cleanup temporary directories
            for temp_dir in self.temp_dirs:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")

    def _send_progress(self, stage: str, progress: int, message: str):
        """Send progress update via Server-Sent Events."""
        progress_data = {
            "type": "progress",
            "data": {
                "stage": stage,
                "progress": progress,
                "message": message
            }
        }
        # This would be handled by the streaming response in the endpoint
        logger.info(f"Progress: {stage} - {progress}% - {message}")

    def _clone_repository(self, repo_url: str) -> str:
        """Clone repository to temporary directory."""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix="repo_analysis_")
            self.temp_dirs.append(temp_dir)
            
            logger.info(f"Cloning repository: {repo_url}")
            
            # Clone repository
            repo = git.Repo.clone_from(repo_url, temp_dir, depth=1)
            
            logger.info(f"Repository cloned to: {temp_dir}")
            return temp_dir
            
        except Exception as e:
            logger.error(f"Failed to clone repository: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to clone repository: {str(e)}")

    def _analyze_code_structure(self, repo_path: str) -> Dict[str, Any]:
        """Analyze code structure using AST parsing."""
        code_hierarchy = {
            "files": []
        }
        
        repo_dir = Path(repo_path)
        
        # Find all Python files
        python_files = list(repo_dir.rglob("*.py"))
        js_files = list(repo_dir.rglob("*.js"))
        ts_files = list(repo_dir.rglob("*.ts"))
        jsx_files = list(repo_dir.rglob("*.jsx"))
        tsx_files = list(repo_dir.rglob("*.tsx"))
        
        all_files = python_files + js_files + ts_files + jsx_files + tsx_files
        
        logger.info(f"Found {len(all_files)} source files to analyze")
        
        for file_path in all_files:
            try:
                file_info = self._analyze_file(file_path, repo_dir)
                if file_info:
                    code_hierarchy["files"].append(file_info)
            except Exception as e:
                logger.warning(f"Failed to analyze file {file_path}: {str(e)}")
                continue
        
        return code_hierarchy

    def _analyze_file(self, file_path: Path, repo_root: Path) -> Optional[Dict[str, Any]]:
        """Analyze individual file using AST parsing."""
        try:
            relative_path = str(file_path.relative_to(repo_root))
            
            # Determine file type
            file_type = self._get_file_type(file_path.suffix)
            if file_type == "unknown":
                return None
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse AST for Python files
            if file_type == "python":
                return self._analyze_python_file(content, relative_path, file_type)
            else:
                # For non-Python files, do basic analysis
                return self._analyze_generic_file(content, relative_path, file_type)
                
        except Exception as e:
            logger.warning(f"Failed to analyze file {file_path}: {str(e)}")
            return None

    def _get_file_type(self, suffix: str) -> str:
        """Determine file type from extension."""
        suffix = suffix.lower()
        if suffix in ['.py']:
            return 'python'
        elif suffix in ['.js', '.jsx']:
            return 'javascript'
        elif suffix in ['.ts', '.tsx']:
            return 'typescript'
        else:
            return 'unknown'

    def _analyze_python_file(self, content: str, relative_path: str, file_type: str) -> Dict[str, Any]:
        """Analyze Python file using AST."""
        try:
            tree = ast.parse(content)
            
            classes = self._extract_classes_from_ast(tree)
            functions = self._extract_functions_from_ast(tree)
            
            return {
                "path": relative_path,
                "type": file_type,
                "classes": classes,
                "functions": functions
            }
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in {relative_path}: {str(e)}")
            return {
                "path": relative_path,
                "type": file_type,
                "classes": [],
                "functions": []
            }

    def _extract_classes_from_ast(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class information from AST."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append({
                            "name": item.name,
                            "line": item.lineno,
                            "complexity": self._calculate_complexity(item)
                        })
                
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods
                })
        return classes

    def _extract_functions_from_ast(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract function information from AST."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not self._is_function_inside_class(node, tree):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "complexity": self._calculate_complexity(node)
                    })
        return functions

    def _is_function_inside_class(self, function_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if a function is inside a class."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in ast.walk(parent):
                    if child is function_node:
                        return True
        return False

    def _analyze_generic_file(self, content: str, relative_path: str, file_type: str) -> Dict[str, Any]:
        """Basic analysis for non-Python files."""
        # Simple regex-based analysis for JavaScript/TypeScript
        import re
        
        classes = []
        functions = []
        
        # Find class definitions
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            classes.append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1,
                "methods": []  # Would need more complex parsing for methods
            })
        
        # Find function definitions
        func_pattern = r'(?:function\s+|const\s+|let\s+|var\s+)(\w+)\s*['
        for match in re.finditer(func_pattern, content):
            functions.append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1,
                "complexity": 1  # Default complexity for non-Python files
            })
        
        return {
            "path": relative_path,
            "type": file_type,
            "classes": classes,
            "functions": functions
        }

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function/class."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity

    def _calculate_complexity_metrics(self, code_hierarchy: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall complexity metrics."""
        total_complexity = 0
        total_functions = 0
        total_classes = 0
        total_files = len(code_hierarchy["files"])
        
        for file_info in code_hierarchy["files"]:
            for cls in file_info["classes"]:
                total_classes += 1
                for method in cls["methods"]:
                    total_functions += 1
                    total_complexity += method["complexity"]
            
            for func in file_info["functions"]:
                total_functions += 1
                total_complexity += func["complexity"]
        
        avg_complexity = total_complexity / max(total_functions, 1)
        coupling = min((total_classes * 2) / max(total_files, 1), 100)  # Simplified coupling metric
        cohesion = max(100 - coupling, 0)  # Simplified cohesion metric
        
        return {
            "cyclomaticComplexity": round(avg_complexity, 2),
            "coupling": round(coupling, 2),
            "cohesion": round(cohesion, 2),
            "codeSmells": self._detect_code_smells(code_hierarchy)
        }

    def _detect_code_smells(self, code_hierarchy: Dict[str, Any]) -> int:
        """Detect potential code smells."""
        smells = 0
        
        for file_info in code_hierarchy["files"]:
            for cls in file_info["classes"]:
                # Long class name
                if len(cls["name"]) > 30:
                    smells += 1
                
                # Too many methods
                if len(cls["methods"]) > 20:
                    smells += 1
                
                for method in cls["methods"]:
                    # Long method name
                    if len(method["name"]) > 50:
                        smells += 1
                    
                    # High complexity
                    if method["complexity"] > 10:
                        smells += 1
            
            for func in file_info["functions"]:
                # Long function name
                if len(func["name"]) > 50:
                    smells += 1
                
                # High complexity
                if func["complexity"] > 10:
                    smells += 1
        
        return smells

    def _analyze_architecture(self, code_hierarchy: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze architectural patterns and purpose using Ollama."""
        try:
            # Prepare data for LLM analysis
            architecture_data = self._prepare_architecture_data(code_hierarchy, metrics)
            
            # Use Ollama for architectural analysis
            ollama_client = LLMClient(LLMProvider.OLLAMA)
            
            # Generate architectural purpose summary
            architectural_purpose = self._generate_architectural_purpose_ollama(
                architecture_data, ollama_client
            )
            
            # Detect architectural patterns
            detected_patterns = self._detect_architectural_patterns_ollama(
                architecture_data, ollama_client
            )
            
            # Identify potential issues
            potential_issues = self._identify_potential_issues_ollama(
                architecture_data, metrics, ollama_client
            )
            
            return {
                "totalFiles": architecture_data["total_files"],
                "totalClasses": architecture_data["total_classes"],
                "totalFunctions": architecture_data["total_functions"],
                "architecturalPurpose": architectural_purpose,
                "detectedPatterns": detected_patterns,
                "potentialIssues": potential_issues
            }
            
        except Exception as e:
            logger.error(f"Architecture analysis failed: {str(e)}")
            return {}

    def _prepare_architecture_data(self, code_hierarchy: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare architecture data for LLM analysis."""
        return {
            "total_files": len(code_hierarchy["files"]),
            "total_classes": sum(len(f["classes"]) for f in code_hierarchy["files"]),
            "total_functions": sum(len(f["functions"]) for f in code_hierarchy["files"]),
            "avg_complexity": metrics.get("cyclomaticComplexity", 0),
            "coupling": metrics.get("coupling", 0),
            "cohesion": metrics.get("cohesion", 0),
            "code_smells": metrics.get("codeSmells", 0),
            "file_types": list(set(f["type"] for f in code_hierarchy["files"] if f["type"] != "unknown"))
        }

    def _generate_architectural_purpose_ollama(
        self, 
        architecture_data: Dict[str, Any], 
        ollama_client: LLMClient
    ) -> str:
        """Generate architectural purpose using Ollama."""
        try:
            # Format the prompt using the architecture prompts module
            code_structure_summary = self._format_code_structure_summary(architecture_data)
            
            prompt = format_architectural_purpose_prompt(
                {
                    'repository_url': 'Unknown',
                    'analysis_date': 'Unknown',
                    'total_files': architecture_data['total_files'],
                    'total_classes': architecture_data['total_classes'],
                    'total_functions': architecture_data['total_functions'],
                    'avg_complexity': architecture_data['avg_complexity'],
                    'coupling': architecture_data['coupling'],
                    'cohesion': architecture_data['cohesion'],
                    'code_smells': architecture_data['code_smells'],
                    'file_types': architecture_data['file_types']
                },
                code_structure_summary
            )
            
            response = ollama_client.generate_completion(
                system_prompt="You are an expert software architect analyzing codebase architecture.",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=2000,
                json_mode=True
            )
            
            # Parse the JSON response
            try:
                result = json.loads(response['content'])
                return result.get('architectural_purpose', 'Unable to determine architectural purpose.')
            except json.JSONDecodeError:
                logger.warning("Failed to parse Ollama response as JSON")
                return response['content'][:500]  # Return first 500 chars as fallback
                
        except Exception as e:
            logger.error(f"Failed to generate architectural purpose with Ollama: {str(e)}")
            return "Unable to determine architectural purpose due to analysis error."

    def _detect_architectural_patterns_ollama(
        self, 
        architecture_data: Dict[str, Any], 
        ollama_client: LLMClient
    ) -> List[str]:
        """Detect architectural patterns using Ollama."""
        try:
            code_structure = self._format_code_structure_summary(architecture_data)
            
            prompt = format_architectural_patterns_prompt(
                {
                    'total_classes': architecture_data['total_classes'],
                    'total_functions': architecture_data['total_functions'],
                    'avg_complexity': architecture_data['avg_complexity'],
                    'coupling': architecture_data['coupling'],
                    'cohesion': architecture_data['cohesion'],
                    'file_types': architecture_data['file_types'],
                    'class_distribution': 'Balanced distribution across modules'
                },
                code_structure
            )
            
            response = ollama_client.generate_completion(
                system_prompt="You are an expert software architect identifying architectural patterns.",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500,
                json_mode=True
            )
            
            # Parse the JSON response
            try:
                result = json.loads(response['content'])
                if isinstance(result, list):
                    return [pattern.get('pattern', '') for pattern in result if pattern.get('pattern')]
                else:
                    return []
            except json.JSONDecodeError:
                logger.warning("Failed to parse Ollama patterns response as JSON")
                return []
                
        except Exception as e:
            logger.error(f"Failed to detect architectural patterns with Ollama: {str(e)}")
            return []

    def _identify_potential_issues_ollama(
        self, 
        architecture_data: Dict[str, Any], 
        metrics: Dict[str, Any], 
        ollama_client: LLMClient
    ) -> List[str]:
        """Identify potential architectural issues using Ollama."""
        try:
            code_structure = self._format_code_structure_summary(architecture_data)
            
            prompt = format_code_quality_prompt(
                {
                    'complexity': architecture_data['avg_complexity'],
                    'coupling': architecture_data['coupling'],
                    'cohesion': architecture_data['cohesion'],
                    'code_smells': architecture_data['code_smells'],
                    'total_files': architecture_data['total_files']
                },
                code_structure
            )
            
            response = ollama_client.generate_completion(
                system_prompt="You are an expert software architect identifying code quality issues.",
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=1500,
                json_mode=True
            )
            
            # Parse the JSON response
            try:
                result = json.loads(response['content'])
                if isinstance(result, dict) and 'potential_issues' in result:
                    return result['potential_issues']
                else:
                    return []
            except json.JSONDecodeError:
                logger.warning("Failed to parse Ollama issues response as JSON")
                return []
                
        except Exception as e:
            logger.error(f"Failed to identify potential issues with Ollama: {str(e)}")
            return []

    def _format_code_structure_summary(self, architecture_data: Dict[str, Any]) -> str:
        """Format code structure summary for LLM prompts."""
        return f"""
        Codebase Structure:
        - Files: {architecture_data['total_files']}
        - Classes: {architecture_data['total_classes']}
        - Functions: {architecture_data['total_functions']}
        - File Types: {', '.join(architecture_data['file_types'])}
        - Average Complexity: {architecture_data['avg_complexity']:.2f}
        - Coupling Score: {architecture_data['coupling']:.2f}
        - Cohesion Score: {architecture_data['cohesion']:.2f}
        - Code Smells: {architecture_data['code_smells']}
        """

    def _detect_architectural_patterns(self, architecture_data: Dict[str, Any]) -> List[str]:
        """Detect architectural patterns using LLM."""
        patterns = []
        
        # Basic pattern detection based on metrics
        if architecture_data['total_classes'] > 50:
            patterns.append("Large-scale application")
        if architecture_data['avg_complexity'] < 5:
            patterns.append("Well-structured code")
        if architecture_data['coupling'] < 30:
            patterns.append("Loose coupling")
        if architecture_data['cohesion'] > 70:
            patterns.append("High cohesion")
        if 'python' in architecture_data['file_types'] and architecture_data['total_classes'] > 10:
            patterns.append("Object-oriented design")
        
        # Use LLM for more sophisticated pattern detection
        if patterns:
            prompt = f"""
            Based on these codebase characteristics, identify the most likely architectural patterns:
            {', '.join(patterns)}
            
            Also consider:
            - Total Files: {architecture_data['total_files']}
            - File Types: {', '.join(architecture_data['file_types'])}
            - Complexity: {architecture_data['avg_complexity']}
            
            Return a comma-separated list of architectural patterns.
            """
            
            try:
                # Use Ollama for pattern detection as well
                ollama_client = LLMClient(LLMProvider.OLLAMA)
                response = ollama_client.generate_completion(
                    system_prompt="You are an expert software architect identifying architectural patterns.",
                    user_prompt=prompt,
                    temperature=0.3,
                    max_tokens=1000,
                    json_mode=False
                )
                llm_patterns = [p.strip() for p in response['content'].split(',') if p.strip()]
                patterns.extend(llm_patterns)
            except Exception as e:
                logger.warning(f"LLM pattern detection failed: {str(e)}")
        
        return list(set(patterns))  # Remove duplicates

    def _identify_potential_issues(self, architecture_data: Dict[str, Any], metrics: Dict[str, Any]) -> List[str]:
        """Identify potential architectural issues."""
        issues = []
        
        if architecture_data['avg_complexity'] > 10:
            issues.append("High cyclomatic complexity detected")
        if architecture_data['coupling'] > 70:
            issues.append("High coupling - potential maintainability issues")
        if architecture_data['cohesion'] < 30:
            issues.append("Low cohesion - poor module organization")
        if metrics.get('codeSmells', 0) > 20:
            issues.append("Many code smells detected")
        if architecture_data['total_files'] > 1000:
            issues.append("Large codebase - consider modularization")
        
        return issues

    def _store_in_neo4j(self, code_hierarchy: Dict[str, Any], architecture_summary: Dict[str, Any], metrics: Dict[str, Any]):
        """Store analysis results in Neo4j."""
        try:
            # This would integrate with the existing Neo4j service
            # For now, we'll just log the data that would be stored
            logger.info(f"Would store {len(code_hierarchy['files'])} files in Neo4j")
            logger.info(f"Architecture summary: {architecture_summary}")
            logger.info(f"Metrics: {metrics}")
            
            # In a real implementation, you would call:
            # await self.neo4j_service.store_analysis_results(code_hierarchy, architecture_summary, metrics)
            
        except Exception as e:
            logger.error(f"Failed to store in Neo4j: {str(e)}")
            raise


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_repository(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Analyze a GitHub repository and return architectural information."""
    analyzer = ArchitectureAnalyzer()
    
    async def analyze_and_stream():
        """Stream analysis progress and results."""
        try:
            # Start analysis in background
            result = await analyzer.analyze_repository(request)
            
            # Send final result
            yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            error_data = {
                "type": "error",
                "data": {
                    "message": str(e)
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        analyze_and_stream(),
        media_type="text/event-stream"
    )


@router.get("/analyze/{analysis_id}", response_model=AnalysisResult)
async def get_analysis_result(analysis_id: str):
    """Get the result of a previously started analysis."""
    # This would retrieve the analysis result from a database or cache
    # For now, return a placeholder
    raise HTTPException(status_code=404, detail="Analysis result not found")
