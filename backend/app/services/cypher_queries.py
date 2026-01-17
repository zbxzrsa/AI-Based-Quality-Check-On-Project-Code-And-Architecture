"""
Cypher Queries for Architectural Drift Detection
================================================

This module contains Cypher queries for Neo4j to detect:
1. Cyclic Dependencies
2. Layer Violations  
3. Unexpected Dependencies
4. Coupling Metrics

Each query includes detailed explanation of the pattern matching logic.
"""

# ========================================
# 1. CYCLIC DEPENDENCY DETECTION
# ========================================

CYCLIC_DEPENDENCY_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
MATCH path = (m1)-[:DEPENDS_ON*]->(m1)
WHERE length(path) > 1
WITH m1, path, relationships(path) as rels
RETURN m1.name AS module,
       [n IN nodes(path) | n.name] AS cycle_path,
       length(path) AS cycle_length,
       [r IN relationships(path) | type(r)] AS relationship_types,
       [r IN relationships(path) | r.reason] AS dependency_reasons
ORDER BY cycle_length ASC
LIMIT 100
"""

CYCLIC_DEPENDENCY_EXPLANATION = """
Query: CYCLIC_DEPENDENCY_QUERY
==============================

Purpose: Find modules that have circular dependencies

Pattern Matching:
1. MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
   - Find the project node
   - Find all modules it contains

2. MATCH path = (m1)-[:DEPENDS_ON*]->(m1)
   - Find paths starting from module m1 that eventually depend on m1 again
   - The * means "any number of hops" (1 or more)
   - This creates cycles of any length >= 2

3. WHERE length(path) > 1
   - Exclude self-loops (which shouldn't exist anyway)
   - Focus on real cycles with multiple modules

4. RETURN cycle_path, cycle_length, dependency_reasons
   - cycle_path: [Module A, Module B, Module C, Module A]
   - cycle_length: 3 (number of modules in the cycle)
   - dependency_reasons: Why each dependency exists

Results Interpretation:
- cycle_length == 2: Direct circular dependency (A->B->A) - CRITICAL
- cycle_length >= 3: Indirect circular dependency - HIGH severity
- More modules in cycle = More complex to break

Recommended Actions:
- Refactor to extract shared functionality into separate module
- Create facade pattern to break circular dependency
- Invert dependency using dependency injection
"""


# ========================================
# 2. LAYER VIOLATION DETECTION
# ========================================

LAYER_VIOLATION_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
MATCH (m1)-[d1:DEPENDS_ON]->(m2:Module)
MATCH (m2)-[d2:DEPENDS_ON]->(m3:Module)
MATCH (m3)-[:DEPENDS_ON]->(m4:Module)

// Check for direct controller -> repository connection (skipping service)
WHERE (toLower(m1.name) CONTAINS 'controller' OR toLower(m1.type) CONTAINS 'controller')
AND (toLower(m3.name) CONTAINS 'repository' OR toLower(m3.type) CONTAINS 'repository')

// Verify there's no intermediate service layer
AND NOT EXISTS {
    MATCH (m1)-[:DEPENDS_ON]->(svc:Module)
    WHERE (toLower(svc.name) CONTAINS 'service' OR toLower(svc.type) CONTAINS 'service')
    AND (svc)-[:DEPENDS_ON]->(m3)
}

RETURN DISTINCT
    m1.name AS source_module,
    m1.type AS source_type,
    m3.name AS target_module,
    m3.type AS target_type,
    [n IN nodes([m1, m2, m3, m4]) | n.name] AS violation_path,
    [r IN relationships([d1, d2]) | r.reason] AS reasons
LIMIT 50
"""

LAYER_VIOLATION_EXPLANATION = """
Query: LAYER_VIOLATION_QUERY
=============================

Purpose: Detect architectural layer violations where layers are skipped

Common Layer Architecture:
  Controller -> Service -> Repository -> Database
           ↑________X________↑ (VIOLATION: Direct skip)

Pattern Matching:
1. WHERE (toLower(m1.name) CONTAINS 'controller' ...)
   - Identify source module as Controller layer
   - Uses naming convention matching (case-insensitive)

2. AND (toLower(m3.name) CONTAINS 'repository' ...)
   - Identify target module as Repository layer
   - m2 is the intermediate that gets skipped

3. AND NOT EXISTS { MATCH (m1)-[:DEPENDS_ON]->(svc:Module) ... }
   - Verify there's NO service layer between m1 and m3
   - This ensures m2 is not a service layer
   - If service layer exists, the violation is valid usage

4. RETURN violation_path = [Controller, Intermediate, Repository, Next]
   - Shows all modules in the violation path

Results Interpretation:
- violation_type = 'layer_skip': Direct bypass of intermediate layer
- severity = 'high': Indicates architectural degradation
- Multiple violations: Architecture is eroding over time

Recommended Actions:
- Add proper service layer abstraction
- Use dependency injection to enforce layer boundaries
- Implement layer validation in build process
- Add architecture rules to linting tools
"""


# ========================================
# 3. DETAILED CYCLIC DEPENDENCY VARIANTS
# ========================================

# Variant 1: Find ONLY direct 2-hop cycles (most critical)
DIRECT_CYCLES_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
MATCH (m1)-[:DEPENDS_ON]->(m2:Module)
MATCH (m2)-[:DEPENDS_ON]->(m1)
RETURN m1.name AS module_a,
       m2.name AS module_b,
       'DIRECT' AS cycle_type
"""

# Variant 2: Find cycles with specific module types
CYCLIC_SERVICE_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
WHERE toLower(m1.type) CONTAINS 'service'
MATCH path = (m1)-[:DEPENDS_ON*2..5]->(m1)
RETURN m1.name AS service_module,
       length(path) AS cycle_length,
       [n IN nodes(path) | n.name] AS cycle_nodes,
       [r IN relationships(path) | {type: type(r), reason: r.reason}] AS edge_details
"""

# Variant 3: Find cycles involving external dependencies
CROSS_MODULE_CYCLES_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)
MATCH (m1)-[:DEPENDS_ON*1..3]->(external:Module)
WHERE external.isExternal = true
MATCH (external)-[:DEPENDS_ON*1..3]->(m1)
RETURN m1.name AS internal_module,
       external.name AS external_dependency,
       'CROSS_MODULE' AS cycle_type
"""


# ========================================
# 4. LAYER VIOLATION VARIANTS
# ========================================

# Variant 1: Detect all layer violations (not just Controller->Repository)
ALL_LAYER_VIOLATIONS_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(source:Module)
MATCH (source)-[d1:DEPENDS_ON*1..3]->(target:Module)
WHERE source.layer IS NOT NULL 
  AND target.layer IS NOT NULL
  AND source.layer < target.layer - 1
RETURN source.name AS source,
       source.layer AS source_layer,
       target.name AS target,
       target.layer AS target_layer,
       (target.layer - source.layer) AS layers_skipped
ORDER BY layers_skipped DESC
"""

# Variant 2: Detect violations by specific layer transition rules
LAYER_TRANSITION_VIOLATIONS_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m1:Module)-[r:DEPENDS_ON]->(m2:Module)
WHERE NOT (m1.layer_type, m2.layer_type) IN [
    ('controller', 'service'),
    ('service', 'repository'),
    ('repository', 'database'),
    ('domain', 'domain'),
    ('domain', 'external')
]
RETURN m1.name AS source_module,
       m1.layer_type AS source_layer,
       m2.name AS target_module,
       m2.layer_type AS target_layer,
       r.reason AS dependency_reason
"""

# Variant 3: Find modules that violate multiple layer rules
MULTI_VIOLATION_MODULES_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
MATCH (m)-[violation:VIOLATES_LAYER]->(rule:LayerRule)
RETURN m.name AS module_name,
       count(violation) AS violation_count,
       collect(rule.rule_name) AS violated_rules
HAVING violation_count > 1
ORDER BY violation_count DESC
"""


# ========================================
# 5. COUPLING AND STABILITY METRICS
# ========================================

# Calculate Efferent Coupling (EC): How many modules this module depends on
EFFERENT_COUPLING_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
OPTIONAL MATCH (m)-[:DEPENDS_ON]->(dependency:Module)
WITH m, count(DISTINCT dependency) AS EC
RETURN m.name AS module,
       EC AS efferent_coupling,
       CASE WHEN EC > 10 THEN 'HIGH'
            WHEN EC > 5 THEN 'MEDIUM'
            ELSE 'LOW' END AS coupling_level
ORDER BY EC DESC
"""

# Calculate Afferent Coupling (AC): How many modules depend on this module
AFFERENT_COUPLING_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
OPTIONAL MATCH (dependent:Module)-[:DEPENDS_ON]->(m)
WITH m, count(DISTINCT dependent) AS AC
RETURN m.name AS module,
       AC AS afferent_coupling,
       CASE WHEN AC > 10 THEN 'HIGH'
            WHEN AC > 5 THEN 'MEDIUM'
            ELSE 'LOW' END AS dependents_count
ORDER BY AC DESC
"""

# Instability Index: (EC / (EC + AC))
# 0 = Stable (many depend on it), 1 = Unstable (depends on others)
INSTABILITY_INDEX_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
OPTIONAL MATCH (m)-[:DEPENDS_ON]->(dep:Module)
WITH m, count(DISTINCT dep) AS EC
OPTIONAL MATCH (dependent:Module)-[:DEPENDS_ON]->(m)
WITH m, EC, count(DISTINCT dependent) AS AC
RETURN m.name AS module,
       EC AS efferent_coupling,
       AC AS afferent_coupling,
       ROUND(toFloat(EC) / (EC + AC), 3) AS instability_index,
       CASE WHEN EC = 0 AND AC > 0 THEN 'STABLE_CORE'
            WHEN EC > 0 AND AC = 0 THEN 'UNSTABLE_LEAF'
            WHEN EC > 0 AND AC > 0 THEN 'BALANCED'
            ELSE 'ISOLATED' END AS module_role
ORDER BY instability_index DESC
"""


# ========================================
# 6. DEPENDENCY PATH ANALYSIS
# ========================================

# Find longest dependency paths (potential refactoring candidates)
LONGEST_DEPENDENCY_PATHS_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(start:Module)
MATCH path = (start)-[:DEPENDS_ON*1..20]->(end:Module)
WHERE start.name < end.name  // Avoid duplicates
RETURN [n IN nodes(path) | n.name] AS path,
       length(path) AS path_length,
       start.name AS source,
       end.name AS sink
ORDER BY path_length DESC
LIMIT 20
"""

# Find all modules involved in dependency chains
DEPENDENCY_CHAIN_MODULES_QUERY = """
MATCH (p:Project {projectId: $projectId})-[:CONTAINS]->(m:Module)
MATCH (m)-[:DEPENDS_ON*1..]->(downstream:Module)
WITH m, count(DISTINCT downstream) AS reachable_modules
MATCH (upstream:Module)-[:DEPENDS_ON*1..]->(m)
WITH m, reachable_modules, count(DISTINCT upstream) AS depending_modules
RETURN m.name AS module,
       reachable_modules,
       depending_modules,
       reachable_modules + depending_modules AS total_connected
ORDER BY total_connected DESC
LIMIT 30
"""


# ========================================
# 7. SCHEDULED QUERY: WEEKLY DRIFT REPORT
# ========================================

WEEKLY_DRIFT_REPORT_QUERY = """
// Run this weekly to generate comprehensive drift report
WITH datetime() AS report_date

MATCH (p:Project {projectId: $projectId})

// Count cycles
CALL {
    MATCH path = (m1:Module)-[:DEPENDS_ON*]->(m1)
    WHERE length(path) > 1
    RETURN count(DISTINCT m1) AS cycle_count
}

// Count layer violations
CALL {
    MATCH (c:Module)-[:DEPENDS_ON*1..3]->(r:Module)
    WHERE toLower(c.name) CONTAINS 'controller'
      AND toLower(r.name) CONTAINS 'repository'
      AND NOT EXISTS {
          MATCH (c)-[:DEPENDS_ON]->(s:Module)
          WHERE toLower(s.name) CONTAINS 'service'
          AND (s)-[:DEPENDS_ON]->(r)
      }
    RETURN count(DISTINCT c) AS violation_count
}

// Calculate average instability
CALL {
    MATCH (m:Module)
    OPTIONAL MATCH (m)-[:DEPENDS_ON]->(dep:Module)
    WITH m, count(DISTINCT dep) AS EC
    OPTIONAL MATCH (dependent:Module)-[:DEPENDS_ON]->(m)
    WITH EC, count(DISTINCT dependent) AS AC
    RETURN AVG(toFloat(EC) / (EC + AC)) AS avg_instability
}

// Count modules with high instability
CALL {
    MATCH (m:Module)
    OPTIONAL MATCH (m)-[:DEPENDS_ON]->(dep:Module)
    WITH m, count(DISTINCT dep) AS EC
    OPTIONAL MATCH (dependent:Module)-[:DEPENDS_ON]->(m)
    WITH m, EC, count(DISTINCT dependent) AS AC
    WHERE toFloat(EC) / (EC + AC) > 0.7
    RETURN count(DISTINCT m) AS unstable_modules
}

RETURN p.name AS project,
       cycle_count,
       violation_count,
       ROUND(avg_instability, 3) AS average_instability,
       unstable_modules,
       report_date
"""


# ========================================
# 8. HELPER FUNCTIONS
# ========================================

def format_cypher_query(query_template: str, **parameters) -> tuple:
    """
    Format a Cypher query with parameters
    
    Args:
        query_template: Cypher query with $parameter placeholders
        **parameters: Parameter values
        
    Returns:
        (formatted_query, parameters_dict)
    """
    return query_template, parameters


def parse_cycle_result(record):
    """Parse cycle detection result"""
    return {
        'module': record.get('module'),
        'cycle_path': record.get('cycle_path', []),
        'cycle_length': record.get('cycle_length'),
        'severity': 'CRITICAL' if record.get('cycle_length') == 2 else 'HIGH',
        'reasons': record.get('dependency_reasons', [])
    }


def parse_violation_result(record):
    """Parse layer violation result"""
    return {
        'source': record.get('source_module'),
        'target': record.get('target_module'),
        'violation_type': 'LAYER_SKIP',
        'severity': 'HIGH',
        'layers_skipped': record.get('layers_skipped', 1),
        'path': record.get('violation_path', [])
    }


# ========================================
# USAGE EXAMPLES
# ========================================

"""
Example 1: Detect Cyclic Dependencies
=====================================
from app.database.neo4j_db import get_neo4j_driver
from app.services.neo4j_ast_service import Neo4jASTService

async def check_cycles():
    driver = await get_neo4j_driver()
    service = Neo4jASTService(driver)
    
    results = await service.run_query(
        CYCLIC_DEPENDENCY_QUERY,
        projectId='my-project'
    )
    
    for record in results:
        print(f"Cycle found: {record['cycle_path']}")


Example 2: Detect Layer Violations
==================================
async def check_layer_violations():
    driver = await get_neo4j_driver()
    service = Neo4jASTService(driver)
    
    results = await service.run_query(
        LAYER_VIOLATION_QUERY,
        projectId='my-project'
    )
    
    for record in results:
        print(f"Violation: {record['source_module']} -> {record['target_module']}")


Example 3: Generate Weekly Report
=================================
from app.tasks.architectural_drift import detect_architectural_drift

# Schedule with Celery Beat
detect_architectural_drift.apply_async(
    args=['my-project'],
    countdown=0,  # Run immediately or schedule for Monday 2am
    expires=3600
)
"""
