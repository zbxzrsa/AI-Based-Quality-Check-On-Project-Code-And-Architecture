"""
Parser factory for getting appropriate parser by language
"""
from typing import Optional
from app.services.parsers.base_parser import BaseASTParser
from app.services.parsers.python_parser import PythonASTParser
from app.services.parsers.javascript_parser import JavaScriptParser


class ParserFactory:
    """
    Factory for creating appropriate AST parser based on language
    """
    
    _parsers = {
        'python': PythonASTParser,
        'py': PythonASTParser,
        'javascript': JavaScriptParser,
        'js': JavaScriptParser,
        'typescript': JavaScriptParser,
        'ts': JavaScriptParser,
        'jsx': JavaScriptParser,
        'tsx': JavaScriptParser,
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
        parser_class = cls._parsers.get(language_lower)
        
        if parser_class:
            return parser_class()
        
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
