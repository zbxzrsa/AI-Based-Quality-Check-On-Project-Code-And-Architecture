"""
Go AST Parser using tree-sitter
"""
from typing import List, Dict, Any
import subprocess
import json
import shlex
from app.services.parsers.base_parser import BaseASTParser
from app.schemas.ast_models import ParsedFile, Module, Class, Function, Import


class GoParser(BaseASTParser):
    """Parser for Go programming language"""
    
    def __init__(self):
        super().__init__()
        self.language = "Go"
    
    def parse(self, file_path: str, code: str) -> ParsedFile:
        """
        Parse Go source code
        
        Args:
            file_path: Path to the file
            code: Source code content
            
        Returns:
            Parsed file structure
        """
        # Use go/ast via subprocess
        ast_data = self._parse_with_go_ast(code)
        
        # Create module
        module = Module(
            name=self._extract_package_name(code),
            file_id=self._generate_file_id(file_path),
            path=file_path,
            language="Go",
            imports=self._extract_imports(ast_data),
            classes=[],  # Go doesn't have classes
            functions=self._extract_functions(ast_data),
            lines_of_code=len(code.split('\n')),
            comment_ratio=self._calculate_comment_ratio(code),
        )
        
        return ParsedFile(module=module, raw_ast=ast_data)
    
    def _parse_with_go_ast(self, code: str) -> Dict[str, Any]:
        """Parse Go code using go/ast"""
        # Create temporary Go file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.go', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Run Go AST parser (requires Go installed)
            # Use shell=False for security and pass args as list
            parser_script = self._get_parser_script()
            cmd = ['go', 'run', parser_script, temp_file]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,  # Explicitly set shell=False for Bandit
                check=False   # Don't raise exception on non-zero return
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"error": "Go parser timeout"}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON from Go parser"}
        finally:
            os.unlink(temp_file)
    
    def _get_parser_script(self) -> str:
        """Get path to Go AST parser script"""
        return "backend/app/services/parsers/helpers/go_ast_parser.go"
    
    def _extract_package_name(self, code: str) -> str:
        """Extract package name from Go code"""
        for line in code.split('\n'):
            if line.strip().startswith('package '):
                return line.strip().split()[1]
        return "main"
    
    def _extract_imports(self, ast_data: Dict[str, Any]) -> List[Import]:
        """Extract imports from AST"""
        imports = []
        
        for imp in ast_data.get('imports', []):
            imports.append(Import(
                module=imp.get('path', ''),
                alias=imp.get('name'),
                is_external=not imp.get('path', '').startswith('.')
            ))
        
        return imports
    
    def _extract_functions(self, ast_data: Dict[str, Any]) -> List[Function]:
        """Extract functions from AST"""
        functions = []
        
        for func_data in ast_data.get('functions', []):
            # Calculate complexity
            complexity = self._calculate_go_complexity(func_data)
            
            # Extract parameters
            params = [
                {"name": p['name'], "type": p['type']}
                for p in func_data.get('parameters', [])
            ]
            
            # Extract return type
            returns = func_data.get('returns', [])
            return_type = ', '.join(returns) if returns else 'void'
            
            function = Function(
                name=func_data.get('name', ''),
                start_line=func_data.get('start_line', 0),
                end_line=func_data.get('end_line', 0),
                parameters=params,
                return_type=return_type,
                complexity=complexity,
                is_async=func_data.get('is_goroutine', False),
                docstring=func_data.get('doc', ''),
                decorators=[],
                calls_to=[],
            )
            
            functions.append(function)
        
        return functions
    
    def _calculate_go_complexity(self, func_data: Dict[str, Any]) -> int:
        """Calculate cyclomatic complexity for Go function"""
        complexity = 1  # Base complexity
        
        # Count decision points
        body = func_data.get('body', '')
        
        # if statements
        complexity += body.count('if ')
        
        # for loops
        complexity += body.count('for ')
        
        # switch cases
        complexity += body.count('case ')
        
        # logical operators
        complexity += body.count('&&')
        complexity += body.count('||')
        
        # defer statements (adds complexity)
        complexity += body.count('defer ')
        
        # select statements
        complexity += body.count('select ')
        
        return complexity
    
    def _calculate_comment_ratio(self, code: str) -> float:
        """Calculate comment to code ratio"""
        lines = code.split('\n')
        comment_lines = 0
        code_lines = 0
        in_block_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # Block comments
            if stripped.startswith('/*'):
                in_block_comment = True
            
            if in_block_comment:
                comment_lines += 1
                if stripped.endswith('*/'):
                    in_block_comment = False
                continue
            
            # Line comments
            if stripped.startswith('//'):
                comment_lines += 1
            else:
                code_lines += 1
        
        total = comment_lines + code_lines
        return comment_lines / total if total > 0 else 0.0
    
    def extract_dependencies(self, parsed_file: ParsedFile) -> List[str]:
        """Extract dependencies from parsed Go file"""
        dependencies = []
        
        for imp in parsed_file.module.imports:
            if imp.is_external:
                dependencies.append(imp.module)
        
        return dependencies
    
    def calculate_metrics(self, parsed_file: ParsedFile) -> Dict[str, Any]:
        """Calculate Go-specific metrics"""
        functions = parsed_file.module.functions
        
        return {
            "total_functions": len(functions),
            "avg_complexity": sum(f.complexity for f in functions) / len(functions) if functions else 0,
            "max_complexity": max((f.complexity for f in functions), default=0),
            "goroutine_count": sum(1 for f in functions if f.is_async),
            "exported_functions": sum(1 for f in functions if f.name[0].isupper()),
            "lines_of_code": parsed_file.module.lines_of_code,
            "comment_ratio": parsed_file.module.comment_ratio,
        }
