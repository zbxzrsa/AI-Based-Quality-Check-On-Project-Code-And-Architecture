"""
Parser factory for getting appropriate parser by language
"""
from typing import Optional
from app.services.parsers.base_parser import BaseASTParser
from app.services.parsers.python_parser import PythonASTParser
from app.services.parsers.javascript_parser import JavaScriptParser
from app.services.parsers.java_parser import JavaParser
from app.services.parsers.go_parser import GoParser


class ParserFactory:
    """
    Factory for creating appropriate AST parser based on language
    
    Supports:
    - Python (using ast module)
    - JavaScript (using tree-sitter with esprima fallback)
    - TypeScript (using tree-sitter with esprima fallback)
    - Java (using tree-sitter)
    - Go (using tree-sitter)
    """
    
    _parsers = {
        'python': (PythonASTParser, {}),
        'py': (PythonASTParser, {}),
        'javascript': (JavaScriptParser, {'language': 'javascript'}),
        'js': (JavaScriptParser, {'language': 'javascript'}),
        'typescript': (JavaScriptParser, {'language': 'typescript'}),
        'ts': (JavaScriptParser, {'language': 'typescript'}),
        'jsx': (JavaScriptParser, {'language': 'javascript'}),
        'tsx': (JavaScriptParser, {'language': 'typescript'}),
        'java': (JavaParser, {}),
        'go': (GoParser, {}),
    }
    
    @classmethod
    def get_parser(cls, language: str) -> Optional[BaseASTParser]:
        """
        Get parser for specified language
        
        Args:
            language: Language name or file extension
            
        Returns:
            Parser instance or None if unsupported
        """
        language_lower = language.lower().lstrip('.')
        parser_info = cls._parsers.get(language_lower)
        
        if parser_info:
            parser_class, kwargs = parser_info
            return parser_class(**kwargs)
        
        return None
    
    @classmethod
    def get_parser_by_filename(cls, filename: str) -> Optional[BaseASTParser]:
        """
        Get parser based on file extension
        
        Args:
            filename: Source file name
            
        Returns:
            Parser instance or None if unsupported
        """
        if '.' not in filename:
            return None
        
        extension = filename.rsplit('.', 1)[-1]
        return cls.get_parser(extension)
    
    @classmethod
    def supported_languages(cls) -> list[str]:
        """Get list of supported languages"""
        return list(set(cls._parsers.keys()))
    
    @classmethod
    def is_language_supported(cls, language: str) -> bool:
        """
        Check if a language is supported
        
        Args:
            language: Language name or file extension
            
        Returns:
            True if supported, False otherwise
        """
        language_lower = language.lower().lstrip('.')
        return language_lower in cls._parsers
