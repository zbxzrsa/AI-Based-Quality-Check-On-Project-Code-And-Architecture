"""
AST to Neo4j Integration Script

This script implements the core engine for parsing Python code into an Abstract Syntax Tree (AST),
extracting ClassDef, FunctionDef, and Import nodes, and providing Cypher queries for Neo4j insertion
with support for detecting coupling anomalies and cyclic dependencies.
"""
import ast
import os
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from pathlib import Path
from dataclasses import dataclass
import json


@dataclass
class ASTNode:
    """Represents an AST node with Neo4j insertion data"""
    node_type: str
    name: str
    full_name: str
    file_path: str
    line_number: int
    properties: Dict[str, Any]
    cypher_create: str
    cypher_relationships: List[str]


@dataclass
class CouplingAnalysis:
    """Analysis of coupling between components"""
    afferent_coupling: int  # Incoming dependencies
    efferent_coupling: int  # Outgoing dependencies
    instability: float  # Instability metric (0-1)
    abstractness: float  # Abstractness metric (0-1)


class ASTNeo4jIntegration:
    """
    Core engine for AST parsing and Neo4j integration with coupling analysis
    """

    def __init__(self):
        self.nodes: List[ASTNode] = []
        self.relationships: List[Tuple[str, str, str]] = []  # (source_id, target_id, rel_type)
        self.imports: Dict[str, str] = {}  # name -> module
        self.function_calls: List[Tuple[str, str]] = []  # (caller, callee)

    def parse_python_file(self, file_path: str) -> List[ASTNode]:
        """
        Parse a Python file and extract AST nodes

        Args:
            file_path: Path to the Python file to parse

        Returns:
            List of ASTNode objects ready for Neo4j insertion
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        try:
            tree = ast.parse(source_code, filename=file_path)
            self._analyze_ast(tree, file_path, source_code)
            return self.nodes
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {file_path}: {e}")

    def _analyze_ast(self, tree: ast.AST, file_path: str, source_code: str):
        """Analyze the AST and extract nodes"""
        self.nodes = []
        self.relationships = []
        self.imports = {}
        self.function_calls = []

        # Extract file-level information
        file_node = self._create_file_node(file_path, source_code)
        self.nodes.append(file_node)

        # Walk the AST
        analyzer = ASTAnalyzer(file_path, self)
        analyzer.visit(tree)

        # Create relationships
        self._create_relationships()

    def _create_file_node(self, file_path: str, source_code: str) -> ASTNode:
        """Create a file-level node"""
        lines = source_code.split('\n')
        loc = len([line for line in lines if line.strip()])  # Lines of code
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        comment_ratio = comment_lines / loc if loc > 0 else 0

        return ASTNode(
            node_type="File",
            name=os.path.basename(file_path),
            full_name=file_path,
            file_path=file_path,
            line_number=1,
            properties={
                "language": "python",
                "lines_of_code": loc,
                "comment_ratio": round(comment_ratio, 2),
                "extension": ".py"
            },
            cypher_create=f"""
            CREATE (f:File {{
                fileId: $fileId,
                name: $name,
                path: $path,
                language: $language,
                linesOfCode: $linesOfCode,
                commentRatio: $commentRatio
            }})
            """,
            cypher_relationships=[]
        )

    def _create_relationships(self):
        """Create relationships between nodes"""
        # Function calls
        for caller, callee in self.function_calls:
            self.relationships.append((caller, callee, "CALLS"))

        # Inheritance relationships (added during AST analysis)
        # Import dependencies (added during AST analysis)

    def get_cypher_queries_for_insertion(self, project_id: str) -> List[str]:
        """
        Generate Cypher queries for inserting all nodes and relationships into Neo4j

        Args:
            project_id: Project identifier

        Returns:
            List of Cypher queries
        """
        queries = []

        # Create nodes
        for node in self.nodes:
            if node.node_type == "File":
                queries.append(f"""
                MATCH (p:Project {{projectId: '{project_id}'}})
                {node.cypher_create.replace('$fileId', f"'{project_id}::{node.full_name}'")
                                      .replace('$name', f"'{node.name}'")
                                      .replace('$path', f"'{node.full_name}'")
                                      .replace('$language', f"'{node.properties['language']}'")
                                      .replace('$linesOfCode', str(node.properties['lines_of_code']))
                                      .replace('$commentRatio', str(node.properties['comment_ratio']))}
                MERGE (p)-[:CONTAINS {{level: 'file'}}]->(f)
                """)

            elif node.node_type == "Class":
                queries.append(f"""
                MATCH (f:File {{fileId: '{project_id}::{node.file_path}'}})
                MERGE (c:Class {{
                    classId: '{project_id}::{node.file_path}::{node.name}',
                    name: '{node.name}',
                    filePath: '{node.file_path}',
                    startLine: {node.line_number}
                }})
                MERGE (f)-[:CONTAINS {{level: 'class'}}]->(c)
                """)

            elif node.node_type == "Function":
                is_method = node.properties.get('is_method', False)
                queries.append(f"""
                MERGE (fn:Function {{
                    functionId: '{project_id}::{node.file_path}::{node.name}',
                    name: '{node.name}',
                    filePath: '{node.file_path}',
                    startLine: {node.line_number},
                    isMethod: {str(is_method).lower()},
                    isAsync: {str(node.properties.get('is_async', False)).lower()}
                }})
                """)

                # Link to class if it's a method
                if is_method:
                    queries.append(f"""
                    MATCH (c:Class {{classId: '{project_id}::{node.file_path}::{node.properties.get('class_name', '')}'}})
                    MATCH (fn:Function {{functionId: '{project_id}::{node.file_path}::{node.name}'}})
                    MERGE (c)-[:CONTAINS {{level: 'method'}}]->(fn)
                    """)

            elif node.node_type == "Import":
                queries.append(f"""
                MATCH (f:File {{fileId: '{project_id}::{node.file_path}'}})
                MERGE (imp:Import {{
                    importId: '{project_id}::{node.file_path}::{node.name}',
                    module: '{node.properties.get('module', '')}',
                    name: '{node.name}',
                    alias: '{node.properties.get('alias', '')}'
                }})
                MERGE (f)-[:CONTAINS {{level: 'import'}}]->(imp)
                MERGE (target:Module {{moduleId: '{node.properties.get('module', '')}'}})
                MERGE (f)-[:DEPENDS_ON {{type: 'import', weight: 1.0}}]->(target)
                """)

        # Create relationships
        for source_id, target_id, rel_type in self.relationships:
            if rel_type == "CALLS":
                queries.append(f"""
                MATCH (caller:Function {{functionId: '{source_id}'}})
                MATCH (callee:Function {{functionId: '{target_id}'}})
                MERGE (caller)-[r:CALLS]->(callee)
                ON CREATE SET r.frequency = 1
                ON MATCH SET r.frequency = r.frequency + 1
                """)
            elif rel_type == "INHERITS_FROM":
                queries.append(f"""
                MATCH (child:Class {{classId: '{source_id}'}})
                MATCH (parent:Class {{classId: '{target_id}'}})
                MERGE (child)-[:INHERITS_FROM]->(parent)
                """)

        return queries

    def detect_coupling_anomalies(self, project_id: str) -> Dict[str, Any]:
        """
        Detect coupling anomalies in the codebase

        Returns:
            Dictionary with coupling analysis results
        """
        coupling_queries = [
            f"""
            // Calculate coupling metrics for all modules
            MATCH (p:Project {{projectId: '{project_id}'}})-[:CONTAINS*]->(m:Module)
            OPTIONAL MATCH (m)-[out:DEPENDS_ON]->()
            WITH m, count(DISTINCT out) AS efferent
            OPTIONAL MATCH ()-[inc:DEPENDS_ON]->(m)
            WITH m, efferent, count(DISTINCT inc) AS afferent
            RETURN m.name AS module,
                   afferent,
                   efferent,
                   CASE WHEN afferent + efferent = 0 THEN 0.0
                        ELSE toFloat(efferent) / (afferent + efferent)
                   END AS instability
            ORDER BY instability DESC
            """,
            f"""
            // Find highly coupled components (instability > 0.8)
            MATCH (p:Project {{projectId: '{project_id}'}})-[:CONTAINS*]->(m:Module)
            OPTIONAL MATCH (m)-[out:DEPENDS_ON]->()
            WITH m, count(DISTINCT out) AS efferent
            OPTIONAL MATCH ()-[inc:DEPENDS_ON]->(m)
            WITH m, efferent, count(DISTINCT inc) AS afferent
            WITH m, afferent, efferent,
                 CASE WHEN afferent + efferent = 0 THEN 0.0
                      ELSE toFloat(efferent) / (afferent + efferent)
                 END AS instability
            WHERE instability > 0.8
            RETURN m.name AS unstable_module,
                   afferent,
                   efferent,
                   instability,
                   'High instability - consider refactoring' AS recommendation
            """,
            f"""
            // Find tightly coupled components (many bidirectional dependencies)
            MATCH (p:Project {{projectId: '{project_id}'}})-[:CONTAINS*]->(a)
            MATCH (a)-[:DEPENDS_ON]->(b)
            MATCH (b)-[:DEPENDS_ON]->(a)
            WHERE id(a) < id(b)  // Avoid duplicate pairs
            RETURN a.name AS component_a,
                   b.name AS component_b,
                   'Bidirectional dependency detected' AS coupling_type
            """
        ]

        return {
            "coupling_analysis_queries": coupling_queries,
            "anomaly_detection": {
                "high_instability_threshold": 0.8,
                "bidirectional_coupling": "Indicates tight coupling",
                "circular_dependencies": "Always problematic"
            }
        }

    def detect_cyclic_dependencies(self, project_id: str) -> Dict[str, Any]:
        """
        Detect cyclic dependencies in the codebase

        Returns:
            Dictionary with cyclic dependency analysis
        """
        cycle_queries = [
            f"""
            // Find all circular dependencies
            MATCH (p:Project {{projectId: '{project_id}'}})-[:CONTAINS*]->(m:Module)
            MATCH path = (m)-[:DEPENDS_ON*2..10]->(m)
            WITH m, path, nodes(path) AS pathNodes, length(path) AS cycleLength
            RETURN m.name AS startModule,
                   [n IN pathNodes | CASE
                       WHEN n:Module THEN n.name
                       WHEN n:File THEN n.path
                       ELSE 'Unknown'
                   END] AS cyclePath,
                   cycleLength
            ORDER BY cycleLength ASC
            LIMIT 20
            """,
            f"""
            // Find strongly connected components (complex cycles)
            MATCH (p:Project {{projectId: '{project_id}'}})-[:CONTAINS*]->(n)
            MATCH path = (n)-[:DEPENDS_ON*]->(n)
            WITH n, collect(path) AS paths
            WHERE size(paths) > 0
            RETURN n.name AS component,
                   size(paths) AS cycleCount,
                   'Strongly connected component' AS issueType
            """
        ]

        return {
            "cycle_detection_queries": cycle_queries,
            "cycle_analysis": {
                "short_cycles": "Easiest to break",
                "long_cycles": "Complex refactoring needed",
                "strongly_connected": "Highly coupled components"
            }
        }


class ASTAnalyzer(ast.NodeVisitor):
    """AST visitor that extracts code structure information"""

    def __init__(self, file_path: str, integration: ASTNeo4jIntegration):
        self.file_path = file_path
        self.integration = integration
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None

    def visit_Import(self, node: ast.Import) -> None:
        """Handle import statements"""
        for name in node.names:
            import_node = ASTNode(
                node_type="Import",
                name=name.name,
                full_name=name.name,
                file_path=self.file_path,
                line_number=node.lineno,
                properties={
                    "module": name.name,
                    "alias": name.asname or "",
                    "import_type": "import"
                },
                cypher_create="",  # Handled in get_cypher_queries
                cypher_relationships=[]
            )
            self.integration.nodes.append(import_node)
            self.integration.imports[name.asname or name.name] = name.name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle from ... import ... statements"""
        module = node.module or ''
        for name in node.names:
            full_name = f"{module}.{name.name}" if module else name.name
            import_node = ASTNode(
                node_type="Import",
                name=name.name,
                full_name=full_name,
                file_path=self.file_path,
                line_number=node.lineno,
                properties={
                    "module": module,
                    "alias": name.asname or "",
                    "import_type": "from_import",
                    "level": node.level
                },
                cypher_create="",
                cypher_relationships=[]
            )
            self.integration.nodes.append(import_node)
            self.integration.imports[name.asname or name.name] = full_name

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handle class definitions"""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_attribute_name(base))

        class_node = ASTNode(
            node_type="Class",
            name=node.name,
            full_name=f"{self.file_path}::{node.name}",
            file_path=self.file_path,
            line_number=node.lineno,
            properties={
                "bases": bases,
                "docstring": ast.get_docstring(node) or ""
            },
            cypher_create="",
            cypher_relationships=[]
        )
        self.integration.nodes.append(class_node)

        # Create inheritance relationships
        for base in bases:
            # Try to resolve base class to a full identifier
            base_id = f"{self.file_path}::{base}"  # Simplified - in real implementation would resolve imports
            self.integration.relationships.append(
                (f"{self.file_path}::{node.name}", base_id, "INHERITS_FROM")
            )

        previous_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions"""
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async function definitions"""
        self._process_function(node, is_async=True)

    def _process_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool) -> None:
        """Process function/method definition"""
        args = []
        if node.args.args:
            args.extend(arg.arg for arg in node.args.args)
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwonlyargs:
            args.extend(arg.arg for arg in node.args.kwonlyargs)
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        returns = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                returns = node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                returns = self._get_attribute_name(node.returns)

        is_method = self.current_class is not None
        full_name = f"{self.current_class}.{node.name}" if is_method else node.name

        function_node = ASTNode(
            node_type="Function",
            name=node.name,
            full_name=full_name,
            file_path=self.file_path,
            line_number=node.lineno,
            properties={
                "args": args,
                "returns": returns,
                "is_async": is_async,
                "is_method": is_method,
                "class_name": self.current_class,
                "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                "docstring": ast.get_docstring(node) or ""
            },
            cypher_create="",
            cypher_relationships=[]
        )
        self.integration.nodes.append(function_node)

        previous_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = previous_function

    def visit_Call(self, node: ast.Call) -> None:
        """Handle function calls"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = self._get_attribute_name(node.func)
        else:
            return

        if self.current_function:
            caller_id = f"{self.file_path}::{self.current_function}"
            # Simplified - in real implementation would resolve the callee
            callee_id = f"{self.file_path}::{func_name}"
            self.integration.function_calls.append((caller_id, callee_id))

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full name of an attribute (e.g., module.Class)"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return node.attr

    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Get decorator name"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return self._get_attribute_name(decorator)
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""


def main():
    """Example usage of the AST Neo4j Integration"""
    integration = ASTNeo4jIntegration()

    # Example: Parse this file itself
    try:
        nodes = integration.parse_python_file(__file__)
        print(f"Extracted {len(nodes)} AST nodes")

        # Generate Cypher queries
        queries = integration.get_cypher_queries_for_insertion("test-project")
        print(f"Generated {len(queries)} Cypher queries")

        # Get coupling analysis
        coupling = integration.detect_coupling_anomalies("test-project")
        print("Coupling analysis queries generated")

        # Get cycle detection
        cycles = integration.detect_cyclic_dependencies("test-project")
        print("Cycle detection queries generated")

        # Print sample queries
        print("\nSample Cypher queries:")
        for i, query in enumerate(queries[:3]):
            print(f"{i+1}. {query.strip()[:100]}...")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
