"""
Code Entity Extraction Demo

This script demonstrates how to use the CodeEntityExtractor service
to extract code entities, calculate complexity, and identify dependencies.
"""
import logging
logger = logging.getLogger(__name__)

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.code_entity_extractor import CodeEntityExtractor


def demo_single_file_extraction():
    """Demonstrate extracting entities from a single file"""
    logger.info("=" * 80)
    logger.info("DEMO: Single File Entity Extraction")
    logger.info("=" * 80)
    
    extractor = CodeEntityExtractor()
    
    # Extract from this demo file itself
    file_path = __file__
    result = extractor.extract_from_file(file_path)
    
    if result["errors"]:
        logger.info("Errors: {result['errors']}")
        return
    
    logger.info("\nFile: {file_path}")
    logger.info("Total entities extracted: {len(result['entities'])}")
    
    # Show entities by type
    functions = [e for e in result["entities"] if e.entity_type == "function"]
    classes = [e for e in result["entities"] if e.entity_type == "class"]
    methods = [e for e in result["entities"] if e.entity_type == "method"]
    
    logger.info("\nFunctions: {len(functions)}")
    for func in functions:
        logger.info("  - {func.name} (complexity: {func.complexity}, LOC: {func.lines_of_code})")
    
    logger.info("\nClasses: {len(classes)}")
    for cls in classes:
        logger.info("  - {cls.name} (complexity: {cls.complexity}, LOC: {cls.lines_of_code})")
    
    logger.info("\nMethods: {len(methods)}")
    for method in methods:
        logger.info("  - {method.name} (complexity: {method.complexity}, LOC: {method.lines_of_code})")
    
    # Show metrics
    logger.info("\nMetrics:")
    metrics = result["metrics"]
    for key, value in metrics.items():
        if isinstance(value, float):
            logger.info("  {key}: {value:.2f}")
        elif isinstance(value, list):
            logger.info("  {key}: {len(value)} items")
        else:
            logger.info("  {key}: {value}")


def demo_high_complexity_detection():
    """Demonstrate finding high complexity entities"""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO: High Complexity Detection")
    logger.info("=" * 80)
    
    extractor = CodeEntityExtractor()
    
    # Create sample code with varying complexity
    sample_code = '''
def simple_function():
    """Complexity: 1"""
    return 42

def moderate_function(x):
    """Complexity: 2"""
    if x > 0:
        return x * 2
    return 0

def complex_function(a, b, c):
    """Complexity: 7"""
    result = 0
    if a > 0:
        if b > 0:
            if c > 0:
                result = a + b + c
            else:
                result = a + b
        else:
            result = a
    elif b > 0:
        result = b
    else:
        result = c
    return result
'''
    
    # Write to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        temp_path = f.name
    
    try:
        result = extractor.extract_from_file(temp_path)
        entities = result["entities"]
        
        logger.info("\nTotal entities: {len(entities)}")
        
        # Find high complexity entities (threshold: 3)
        high_complexity = extractor.find_high_complexity_entities(entities, threshold=3)
        
        logger.info("\nHigh complexity entities (complexity > 3): {len(high_complexity)}")
        for entity in high_complexity:
            logger.info("  - {entity.name}: complexity = {entity.complexity}")
        
        # Show complexity distribution
        complexities = [e.complexity for e in entities]
        logger.info("\nComplexity statistics:")
        logger.info("  Min: {min(complexities)}")
        logger.info("  Max: {max(complexities)}")
        logger.info("  Avg: {sum(complexities) / len(complexities):.2f}")
    
    finally:
        import os
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def demo_dependency_graph():
    """Demonstrate building dependency graphs"""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO: Dependency Graph Construction")
    logger.info("=" * 80)
    
    extractor = CodeEntityExtractor()
    
    # Create sample files with dependencies
    module_a = '''
"""Module A"""

class BaseClass:
    def base_method(self):
        return "base"

def utility_function():
    return 42
'''
    
    module_b = '''
"""Module B"""
from module_a import BaseClass, utility_function

class DerivedClass(BaseClass):
    def derived_method(self):
        result = utility_function()
        return result + 1

def another_function():
    obj = DerivedClass()
    return obj.base_method()
'''
    
    # Write to temp files
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f1:
        f1.write(module_a)
        path1 = f1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f2:
        f2.write(module_b)
        path2 = f2.name
    
    try:
        result = extractor.extract_from_files([path1, path2])
        
        logger.info("\nTotal files analyzed: {len(result['parsed_files'])}")
        logger.info("Total entities: {len(result['entities'])}")
        
        # Show dependency graph
        graph = result["dependency_graph"]
        logger.info("\nDependency Graph:")
        logger.info("  Nodes: {len(graph.nodes)}")
        logger.info("  Edges: {len(graph.edges)}")
        
        logger.info("\nDependencies:")
        for edge in graph.edges:
            logger.info("  {edge.source} --[{edge.type}]--> {edge.target}")
        
        # Show graph metrics
        logger.info("\nGraph Metrics:")
        for key, value in graph.metrics.items():
            if isinstance(value, float):
                logger.info("  {key}: {value:.2f}")
            else:
                logger.info("  {key}: {value}")
        
        # Show cross-file metrics
        logger.info("\nCross-File Metrics:")
        metrics = result["metrics"]
        for key, value in metrics.items():
            if key == "high_complexity_entities":
                logger.info("  {key}: {len(value)} entities")
            elif key == "graph_metrics":
                continue  # Already shown above
            elif isinstance(value, float):
                logger.info("  {key}: {value:.2f}")
            else:
                logger.info("  {key}: {value}")
    
    finally:
        if os.path.exists(path1):
            os.unlink(path1)
        if os.path.exists(path2):
            os.unlink(path2)


def demo_entity_filtering():
    """Demonstrate filtering entities"""
    logger.info("\n" + "=" * 80)
    logger.info("DEMO: Entity Filtering")
    logger.info("=" * 80)
    
    extractor = CodeEntityExtractor()
    
    sample_code = '''
class MyClass:
    def method_one(self):
        return 1
    
    def method_two(self):
        return 2

def standalone_function():
    return 3

def another_function():
    return 4
'''
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        temp_path = f.name
    
    try:
        result = extractor.extract_from_file(temp_path)
        entities = result["entities"]
        
        logger.info("\nTotal entities: {len(entities)}")
        
        # Filter by type
        functions = extractor.get_entities_by_type(entities, "function")
        classes = extractor.get_entities_by_type(entities, "class")
        methods = extractor.get_entities_by_type(entities, "method")
        
        logger.info("\nFiltered by type:")
        logger.info("  Functions: {len(functions)}")
        for func in functions:
            logger.info("    - {func.name}")
        
        logger.info("  Classes: {len(classes)}")
        for cls in classes:
            logger.info("    - {cls.name}")
        
        logger.info("  Methods: {len(methods)}")
        for method in methods:
            logger.info("    - {method.name}")
    
    finally:
        import os
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def main():
    """Run all demos"""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 20 + "CODE ENTITY EXTRACTION DEMO" + " " * 31 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    try:
        demo_single_file_extraction()
        demo_high_complexity_detection()
        demo_dependency_graph()
        demo_entity_filtering()
        
        logger.info("\n" + "=" * 80)
        logger.info("All demos completed successfully!")
        logger.info("=" * 80 + "\n")
    
    except Exception as e:
        logger.info("\nError running demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
