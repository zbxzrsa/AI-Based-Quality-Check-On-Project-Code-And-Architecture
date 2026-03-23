"""
C# AST Parser using tree-sitter-c-sharp
"""
from typing import List, Dict, Any
from app.services.parsers.base_parser import BaseASTParser
from app.schemas.ast_models import ParsedFile, Module, Class, Function, Import
import re


class CSharpParser(BaseASTParser):
    """Parser for C# programming language"""
    
    def __init__(self):
        super().__init__()
        self.language = "C#"
    
    def parse(self, file_path: str, code: str) -> ParsedFile:
        """
        Parse C# source code
        
        Args:
            file_path: Path to the file
            code: Source code content
            
        Returns:
            Parsed file structure
        """
        # Create module
        module = Module(
            name=self._extract_namespace(code),
            file_id=self._generate_file_id(file_path),
            path=file_path,
            language="C#",
            imports=self._extract_usings(code),
            classes=self._extract_classes(code),
            functions=[],  # Top-level functions in global namespace
            lines_of_code=len(code.split('\n')),
            comment_ratio=self._calculate_comment_ratio(code),
        )
        
        return ParsedFile(module=module, raw_ast={})
    
    def _extract_namespace(self, code: str) -> str:
        """Extract namespace from C# code"""
        # Match: namespace MyApp.Services { }
        namespace_pattern = r'namespace\s+([\w\.]+)'
        match = re.search(namespace_pattern, code)
        return match.group(1) if match else "Global"
    
    def _extract_usings(self, code: str) -> List[Import]:
        """Extract using statements"""
        imports = []
        
        # Match: using System.Collections;
        using_pattern = r'using\s+([\w\.]+);'
        
        for match in re.finditer(using_pattern, code):
            namespace = match.group(1)
            imports.append(Import(
                module=namespace,
                alias=None,
                is_external=not namespace.startswith('.')
            ))
        
        # Match: using Alias = System.Collections.Generic;
        alias_pattern = r'using\s+(\w+)\s*=\s*([\w\.]+);'
        
        for match in re.finditer(alias_pattern, code):
            alias = match.group(1)
            namespace = match.group(2)
            imports.append(Import(
                module=namespace,
                alias=alias,
                is_external=True
            ))
        
        return imports
    
    def _extract_classes(self, code: str) -> List[Class]:
        """Extract classes from C# code"""
        classes = []
        
        # Complex regex for class definition
        class_pattern = r'''
            (?:public|private|protected|internal)?\s*
            (?:static|abstract|sealed)?\s*
            (?:partial)?\s*
            class\s+
            (\w+)                           # Class name
            (?:\s*:\s*([\w\s,<>]+))?        # Base class/interfaces
            \s*\{
        '''
        
        for match in re.finditer(class_pattern, code, re.VERBOSE | re.MULTILINE):
            class_name = match.group(1)
            base_classes = match.group(2)
            
            # Extract class body
            class_start = match.end()
            class_body = self._extract_block(code, class_start)
            
            # Parse methods
            methods = self._extract_methods(class_body, class_name)
            
            # Parse properties
            properties = self._extract_properties(class_body)
            
            # Calculate start/end lines
            start_line = code[:match.start()].count('\n') + 1
            end_line = code[:class_start + len(class_body)].count('\n') + 1
            
            classes.append(Class(
                name=class_name,
                bases=base_classes.split(',') if base_classes else [],
                methods=methods,
                attributes=properties,
                start_line=start_line,
                end_line=end_line,
                docstring=self._extract_class_doc(code, match.start()),
                decorators=self._extract_attributes(code, match.start()),
                is_abstract='abstract' in code[max(0, match.start()-50):match.start()],
            ))
        
        return classes
    
    def _extract_methods(self, class_body: str, class_name: str) -> List[Function]:
        """Extract methods from class body"""
        methods = []
        
        # Method pattern
        method_pattern = r'''
            (?:public|private|protected|internal)?\s*
            (?:static|virtual|override|abstract)?\s*
            (?:async)?\s*
            ([\w<>\[\]]+)\s+                # Return type
            (\w+)\s*                        # Method name
            \(([^)]*)\)                     # Parameters
        '''
        
        for match in re.finditer(method_pattern, class_body, re.VERBOSE):
            return_type = match.group(1)
            method_name = match.group(2)
            params_str = match.group(3)
            
            # Skip properties (get/set)
            if method_name in ['get', 'set']:
                continue
            
            # Parse parameters
            parameters = self._parse_csharp_parameters(params_str)
            
            # Calculate complexity
            method_start = match.end()
            method_body = self._extract_block(class_body, method_start)
            complexity = self._calculate_csharp_complexity(method_body)
            
            # Calculate lines
            start_line = class_body[:match.start()].count('\n') + 1
            end_line = class_body[:method_start + len(method_body)].count('\n') + 1
            
            methods.append(Function(
                name=f"{class_name}.{method_name}",
                start_line=start_line,
                end_line=end_line,
                parameters=parameters,
                return_type=return_type,
                complexity=complexity,
                is_async='async' in class_body[max(0, match.start()-30):match.start()],
                docstring=self._extract_method_doc(class_body, match.start()),
                decorators=self._extract_attributes(class_body, match.start()),
                calls_to=[],
            ))
        
        return methods
    
    def _extract_properties(self, class_body: str) -> List[Dict[str, Any]]:
        """Extract C# properties"""
        properties = []
        
        # Property pattern: public string Name { get; set; }
        prop_pattern = r'(?:public|private|protected)\s+([\w<>]+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}'
        
        for match in re.finditer(prop_pattern, class_body):
            prop_type = match.group(1)
            prop_name = match.group(2)
            
            properties.append({
                "name": prop_name,
                "type": prop_type,
                "is_property": True
            })
        
        return properties
    
    def _parse_csharp_parameters(self, params_str: str) -> List[Dict[str, Any]]:
        """Parse C# method parameters"""
        if not params_str.strip():
            return []
        
        parameters = []
        
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue
            
            # Parse: int x, string name = "default"
            parts = param.split()
            if len(parts) >= 2:
                param_type = parts[0]
                param_name = parts[1].split('=')[0]  # Remove default value
                
                parameters.append({
                    "name": param_name,
                    "type": param_type
                })
        
        return parameters
    
    def _calculate_csharp_complexity(self, body: str) -> int:
        """Calculate cyclomatic complexity for C#"""
        complexity = 1
        
        # Decision points
        complexity += body.count('if ')
        complexity += body.count('else if')
        complexity += body.count('for ')
        complexity += body.count('foreach ')
        complexity += body.count('while ')
        complexity += body.count('case ')
        complexity += body.count('catch ')
        complexity += body.count('&&')
        complexity += body.count('||')
        complexity += body.count('?')  # Ternary
        
        return complexity
    
    def _extract_block(self, code: str, start: int) -> str:
        """Extract code block starting from position"""
        brace_count = 0
        for i in range(start, len(code)):
            if code[i] == '{':
                brace_count += 1
            elif code[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return code[start:i+1]
        return ""
    
    def _extract_class_doc(self, code: str, class_start: int) -> str:
        """Extract XML documentation comment for class"""
        # Look backwards for /// comments
        lines = code[:class_start].split('\n')
        doc_lines = []
        
        for line in reversed(lines[-10:]):  # Check last 10 lines
            if line.strip().startswith('///'):
                doc_lines.insert(0, line.strip()[3:].strip())
            elif doc_lines:
                break
        
        return '\n'.join(doc_lines)
    
    def _extract_method_doc(self, code: str, method_start: int) -> str:
        """Extract XML documentation comment for method"""
        return self._extract_class_doc(code, method_start)
    
    def _extract_attributes(self, code: str, start: int) -> List[str]:
        """Extract C# attributes [Attribute]"""
        attributes = []
        
        # Look backwards for [Attribute]
        lines = code[:start].split('\n')
        
        for line in reversed(lines[-5:]):
            if line.strip().startswith('[') and line.strip().endswith(']'):
                attr = line.strip()[1:-1]
                attributes.append(attr)
            elif attributes:
                break
        
        return attributes
    
    def _calculate_comment_ratio(self, code: str) -> float:
        """Calculate comment ratio for C#"""
        lines = code.split('\n')
        comment_lines = 0
        code_lines = 0
        in_block_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
            
            # Block comments
            if '/*' in stripped:
                in_block_comment = True
            
            if in_block_comment:
                comment_lines += 1
                if '*/' in stripped:
                    in_block_comment = False
                continue
            
            # Line comments (// and ///)
            if stripped.startswith('//'):
                comment_lines += 1
            else:
                code_lines += 1
        
        total = comment_lines + code_lines
        return comment_lines / total if total > 0 else 0.0
    
    def extract_dependencies(self, parsed_file: ParsedFile) -> List[str]:
        """Extract dependencies from C# file"""
        return [imp.module for imp in parsed_file.module.imports if imp.is_external]
    
    def calculate_metrics(self, parsed_file: ParsedFile) -> Dict[str, Any]:
        """Calculate C#-specific metrics"""
        classes = parsed_file.module.classes
        all_methods = []
        
        for cls in classes:
            all_methods.extend(cls.methods)
        
        return {
            "total_classes": len(classes),
            "total_methods": len(all_methods),
            "avg_complexity": sum(m.complexity for m in all_methods) / len(all_methods) if all_methods else 0,
            "max_complexity": max((m.complexity for m in all_methods), default=0),
            "async_methods": sum(1 for m in all_methods if m.is_async),
            "abstract_classes": sum(1 for c in classes if c.is_abstract),
            "lines_of_code": parsed_file.module.lines_of_code,
            "comment_ratio": parsed_file.module.comment_ratio,
        }
