"""
Utility for classifying architectural layers based on naming conventions and project structure.
"""
from typing import Tuple

class LayerClassifier:
    """
    Classifies modules into architectural layers.
    Used during Neo4j ingestion to set indexed properties on nodes.
    """
    
    # Layer definitions and their relative ranks (lower rank = higher level/outer layer)
    LAYERS = {
        'controller': 1,
        'api': 1,
        'router': 1,
        'endpoint': 1,
        'service': 2,
        'manager': 2,
        'logic': 2,
        'repository': 3,
        'data': 3,
        'dao': 3,
        'model': 4,
        'entity': 4,
        'schema': 4,
        'util': 5,
        'common': 5,
        'shared': 5,
        'external': 6
    }
    
    @staticmethod
    def classify_module(module_name: str) -> Tuple[str, int]:
        """
        Determine the layer type and rank of a module from its name.
        
        Returns:
            (layer_type, layer_rank) - defaults to ('unknown', 99) if no match found.
        """
        name_lower = module_name.lower()
        
        # Check for explicit keywords in the module name
        for layer_type, rank in LayerClassifier.LAYERS.items():
            if layer_type in name_lower:
                return layer_type, rank
        
        # Heuristics based on package structure patterns (e.g., app.v1.endpoints.auth)
        if 'endpoints' in name_lower or 'v1' in name_lower:
            return 'api', 1
        if 'database' in name_lower or 'schemas' in name_lower:
            return 'model', 4
            
        return 'unknown', 99

# Global instance for easy use
layer_classifier = LayerClassifier()
