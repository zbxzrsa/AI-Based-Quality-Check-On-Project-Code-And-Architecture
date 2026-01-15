"""
Sample test file for Python AST parser
"""
import pytest
from pathlib import Path
from app.services.parsers.python_parser import PythonASTParser


# Sample Python code for testing
SAMPLE_PYTHON_CODE = '''
"""Sample module for testing"""
import os
import sys
from typing import List, Dict

class Calculator:
    """A sample calculator class"""
    
    def __init__(self, initial_value: int = 0):
        self.value = initial_value
    
    def add(self, x: int, y: int) -> int:
        """Add two numbers"""
        result = x + y
        return result
    
    def calculate_fibonacci(self, n: int) -> List[int]:
        """Calculate Fibonacci sequence"""
        if n <= 0:
            return []
        elif n == 1:
            return [0]
        elif n == 2:
            return [0, 1]
        
        fib = [0, 1]
        for i in range(2, n):
            fib.append(fib[i-1] + fib[i-2])
        
        return fib

def complex_function(data: Dict, threshold: int = 10) -> bool:
    """A complex function for testing complexity calculation"""
    result = False
    
    if data and len(data) > 0:
        for key, value in data.items():
            if isinstance(value, int):
                if value > threshold:
                    result = True
                    break
            elif isinstance(value, str):
                try:
                    num = int(value)
                    if num > threshold:
                        result = True
                except ValueError:
                    pass
    
    return result

async def async_function():
    """An async function"""
    await some_async_call()
    return "done"
'''


def test_parse_python_file():
    """Test parsing Python code"""
    parser = PythonASTParser()
    
    # Parse the sample code
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    assert result.errors == [], f"Parse errors: {result.errors}"
    assert result.module.language == "python"
    assert result.module.name == "test"


def test_extract_imports():
    """Test import extraction"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    imports = result.module.imports
    assert len(imports) >= 2  # At least os and sys
    
    import_names = [imp.module_name for imp in imports]
    assert "os" in import_names
    assert "sys" in import_names


def test_extract_classes():
    """Test class extraction"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    classes = result.module.classes
    assert len(classes) == 1
    assert classes[0].name == "Calculator"
    assert len(classes[0].methods) == 3  # __init__, add, calculate_fibonacci


def test_extract_functions():
    """Test function extraction"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    functions = result.module.functions
    assert len(functions) == 2  # complex_function, async_function
    
    func_names = [f.name for f in functions]
    assert "complex_function" in func_names
    assert "async_function" in func_names


def test_complexity_calculation():
    """Test cyclomatic complexity calculation"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    # Find complex_function
    complex_func = next((f for f in result.module.functions if f.name == "complex_function"), None)
    assert complex_func is not None
    
    # Should have high complexity due to nested if statements
    assert complex_func.complexity > 1
    print(f"Complex function complexity: {complex_func.complexity}")


def test_nesting_depth():
    """Test nesting depth calculation"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    complex_func = next((f for f in result.module.functions if f.name == "complex_function"), None)
    assert complex_func is not None
    assert complex_func.nesting_depth >= 2  # Has nested loops and conditions


def test_async_detection():
    """Test async function detection"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    async_func = next((f for f in result.module.functions if f.name == "async_function"), None)
    assert async_func is not None
    assert async_func.is_async is True


def test_metrics_calculation():
    """Test overall metrics calculation"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    metrics = result.metrics
    assert metrics["total_classes"] == 1
    assert metrics["total_functions"] == 2
    assert metrics["avg_complexity"] > 0
    assert metrics["max_complexity"] > 0


def test_line_counting():
    """Test line counting"""
    parser = PythonASTParser()
    result = parser.parse_file("test.py", content=SAMPLE_PYTHON_CODE)
    
    module = result.module
    assert module.lines_of_code > 0
    assert module.comment_lines > 0
    assert module.blank_lines >= 0
    assert 0 <= module.comment_ratio <= 1


def test_error_handling():
    """Test handling of syntax errors"""
    parser = PythonASTParser()
    
    # Invalid Python code
    invalid_code = "def broken function(:"
    result = parser.parse_file("broken.py", content=invalid_code)
    
    assert len(result.errors) > 0
    assert "Syntax error" in result.errors[0]


if __name__ == "__main__":
    # Run basic tests
    test_parse_python_file()
    test_extract_imports()
    test_extract_classes()
    test_extract_functions()
    test_complexity_calculation()
    test_nesting_depth()
    test_async_detection()
    test_metrics_calculation()
    test_line_counting()
    test_error_handling()
    
    print("All tests passed!")
