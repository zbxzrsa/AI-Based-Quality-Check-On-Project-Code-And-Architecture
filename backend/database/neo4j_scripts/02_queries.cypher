// ================================================
// Neo4j Cypher Queries
// Advanced queries for code analysis
// ================================================

// ================================================
// 1. INSERT AST NODES AND RELATIONSHIPS
// ================================================

// Insert a new project with modules
// Usage: Replace parameters with actual values
MERGE (p:Project {projectId: $projectId})
SET p.name = $name,
    p.language = $language,
    p.createdAt = datetime()
RETURN p;

// Insert a module into a project
MATCH (p:Project {projectId: $projectId})
MERGE (m:Module {moduleId: $moduleId})
SET m.name = $moduleName,
    m.path = $modulePath,
    m.type = $moduleType
MERGE (p)-[:CONTAINS {level: 'module'}]->(m)
RETURN m;

// Insert a class with its file
MATCH (m:Module {moduleId: $moduleId})
MERGE (f:File {fileId: $fileId})
SET f.path = $filePath,
    f.language = $language,
    f.linesOfCode = $linesOfCode
MERGE (c:Class {classId: $classId})
SET c.name = $className,
    c.filePath = $filePath,
    c.startLine = $startLine,
    c.endLine = $endLine
MERGE (m)-[:CONTAINS {level: 'file'}]->(f)
MERGE (f)-[:CONTAINS {level: 'class'}]->(c)
RETURN c;

// Insert a function/method
MATCH (c:Class {classId: $classId})
MERGE (fn:Function {functionId: $functionId})
SET fn.name = $functionName,
    fn.parameters = $parameters,
    fn.returnType = $returnType,
    fn.complexity = $complexity
MERGE (c)-[:CONTAINS {level: 'method'}]->(fn)
RETURN fn;

// Create dependency relationship
MATCH (source:Module {moduleId: $sourceModuleId})
MATCH (target:Module {moduleId: $targetModuleId})
MERGE (source)-[d:DEPENDS_ON]->(target)
SET d.type = $dependencyType,
    d.weight = $weight
RETURN d;

// Create function call relationship
MATCH (caller:Function {functionId: $callerFunctionId})
MATCH (callee:Function {functionId: $calleeFunctionId})
MERGE (caller)-[c:CALLS]->(callee)
SET c.frequency = coalesce(c.frequency, 0) + 1,
    c.callType = $callType
RETURN c;

// ================================================
// 2. FIND CIRCULAR DEPENDENCIES
// ================================================

// Find all circular dependencies (cycles) in module dependencies
MATCH path = (m1:Module)-[:DEPENDS_ON*]->(m1)
WHERE length(path) > 1
RETURN m1.name AS module,
       [n IN nodes(path) | n.name] AS cycle,
       length(path) AS cycleLength
ORDER BY cycleLength DESC;

// Find circular dependencies with specific length (e.g., 2-node cycles)
MATCH (m1:Module)-[:DEPENDS_ON]->(m2:Module)-[:DEPENDS_ON]->(m1)
WHERE m1.moduleId < m2.moduleId  // Avoid duplicates
RETURN m1.name AS module1,
       m2.name AS module2,
       'Bidirectional dependency' AS issue;

// Find all cycles of any length up to 5
MATCH path = (m:Module)-[:DEPENDS_ON*2..5]->(m)
WITH m, path, nodes(path) AS pathNodes
RETURN m.name AS startModule,
       [n IN pathNodes | n.name] AS cyclePath,
       length(path) AS cycleLength,
       reduce(totalWeight = 0.0, r IN relationships(path) | totalWeight + r.weight) AS totalWeight
ORDER BY cycleLength, totalWeight DESC;

// ================================================
// 3. DETECT ARCHITECTURAL DRIFT
// ================================================

// Find layer violations (e.g., data layer calling presentation layer)
MATCH (lower:Module {type: 'data'})-[:DEPENDS_ON]->(upper:Module {type: 'presentation'})
RETURN lower.name AS violatingModule,
       upper.name AS targetModule,
       'Layer violation: Data layer should not depend on presentation layer' AS issue;

// Find modules with unexpectedly high coupling
MATCH (m:Module)-[d:DEPENDS_ON]->()
WITH m, count(d) AS outgoingDeps
WHERE outgoingDeps > 5  // Threshold for high coupling
RETURN m.name AS module,
       m.path AS path,
       outgoingDeps AS dependencies,
       'High coupling detected' AS warning
ORDER BY outgoingDeps DESC;

// Compare current structure against baseline
// (Assumes baseline snapshot is stored in Project properties)
MATCH (p:Project {projectId: $projectId})
MATCH (p)-[:CONTAINS]->(m:Module)
WITH p, count(m) AS currentModuleCount
WHERE currentModuleCount != p.baselineModuleCount
RETURN 'Module count drift' AS driftType,
       p.baselineModuleCount AS baseline,
       currentModuleCount AS current,
       currentModuleCount - p.baselineModuleCount AS drift;

// Find new VIOLATES relationships (architectural violations)
MATCH ()-[v:VIOLATES]->()
WHERE v.detectedAt > datetime() - duration({days: 7})
RETURN v.violationType AS violationType,
       v.severity AS severity,
       v.description AS description,
       v.detectedAt AS detectedAt
ORDER BY v.severity DESC, v.detectedAt DESC;

// ================================================
// 4. CALCULATE COUPLING METRICS
// ================================================

// Afferent Coupling (Ca) - number of modules that depend on this module
MATCH (m:Module)<-[:DEPENDS_ON]-(dependent:Module)
WITH m, count(DISTINCT dependent) AS afferentCoupling
RETURN m.name AS module,
       afferentCoupling AS ca,
       CASE
           WHEN afferentCoupling > 10 THEN 'Very High'
           WHEN afferentCoupling > 5 THEN 'High'
           WHEN afferentCoupling > 2 THEN 'Medium'
           ELSE 'Low'
       END AS couplingLevel
ORDER BY afferentCoupling DESC;

// Efferent Coupling (Ce) - number of modules this module depends on
MATCH (m:Module)-[:DEPENDS_ON]->(dependency:Module)
WITH m, count(DISTINCT dependency) AS efferentCoupling
RETURN m.name AS module,
       efferentCoupling AS ce,
       CASE
           WHEN efferentCoupling > 10 THEN 'Very High'
           WHEN efferentCoupling > 5 THEN 'High'
           WHEN efferentCoupling > 2 THEN 'Medium'
           ELSE 'Low'
       END AS couplingLevel
ORDER BY efferentCoupling DESC;

// Instability (I = Ce / (Ca + Ce))
MATCH (m:Module)
OPTIONAL MATCH (m)-[:DEPENDS_ON]->(dependency:Module)
WITH m, count(DISTINCT dependency) AS ce
OPTIONAL MATCH (m)<-[:DEPENDS_ON]-(dependent:Module)
WITH m, ce, count(DISTINCT dependent) AS ca
WITH m, ca, ce, ca + ce AS totalCoupling
RETURN m.name AS module,
       ca AS afferentCoupling,
       ce AS efferentCoupling,
       CASE
           WHEN totalCoupling = 0 THEN 0.0
           ELSE toFloat(ce) / totalCoupling
       END AS instability
ORDER BY instability DESC;

// Coupling between modules with weights
MATCH (m1:Module)-[d:DEPENDS_ON]->(m2:Module)
RETURN m1.name AS sourceModule,
       m2.name AS targetModule,
       d.weight AS couplingWeight,
       d.type AS dependencyType
ORDER BY d.weight DESC;

// Overall project coupling metrics
MATCH (p:Project {projectId: $projectId})
MATCH (p)-[:CONTAINS]->(m:Module)
OPTIONAL MATCH (m)-[d:DEPENDS_ON]->()
WITH count(DISTINCT m) AS moduleCount,
     count(d) AS totalDependencies,
     avg(d.weight) AS avgWeight
RETURN moduleCount,
       totalDependencies,
       avgWeight,
       toFloat(totalDependencies) / (moduleCount * (moduleCount - 1)) AS densityRatio;

// ================================================
// 5. FIND CRITICAL PATHS
// ================================================

// Find the most complex functions
MATCH (f:Function)
WHERE f.complexity > 10
RETURN f.name AS functionName,
       f.complexity AS complexity,
       f.parameters AS parameters
ORDER BY f.complexity DESC
LIMIT 20;

// Find critical call chains (deep call stacks)
MATCH path = (caller:Function)-[:CALLS*3..8]->(callee:Function)
WHERE caller.functionId <> callee.functionId
RETURN [n IN nodes(path) | n.name] AS callChain,
       length(path) AS depth,
       reduce(totalComplexity = 0, n IN nodes(path) | totalComplexity + n.complexity) AS totalComplexity
ORDER BY depth DESC, totalComplexity DESC
LIMIT 10;

// Find most frequently called functions (hot paths)
MATCH (caller:Function)-[c:CALLS]->(callee:Function)
WITH callee, sum(c.frequency) AS totalCalls
RETURN callee.name AS functionName,
       callee.complexity AS complexity,
       totalCalls AS callFrequency,
       totalCalls * callee.complexity AS riskScore
ORDER BY riskScore DESC
LIMIT 20;

// Find modules on critical path (many modules depend on them)
MATCH (m:Module)<-[:DEPENDS_ON*]-(dependent:Module)
WITH m, count(DISTINCT dependent) AS dependentCount
WHERE dependentCount > 3
RETURN m.name AS criticalModule,
       m.path AS path,
       dependentCount AS impactedModules
ORDER BY dependentCount DESC;

// Find potential bottlenecks (high in-degree and out-degree)
MATCH (m:Module)
OPTIONAL MATCH (m)-[:DEPENDS_ON]->(out)
WITH m, count(DISTINCT out) AS outDegree
OPTIONAL MATCH (m)<-[:DEPENDS_ON]-(inc)
WITH m, outDegree, count(DISTINCT inc) AS inDegree
WHERE inDegree > 3 AND outDegree > 3
RETURN m.name AS bottleneckModule,
       inDegree AS dependencies,
       outDegree AS dependents,
       inDegree + outDegree AS totalConnections
ORDER BY totalConnections DESC;

// Find longest dependency chains
MATCH path = (start:Module)-[:DEPENDS_ON*]->(end:Module)
WHERE NOT (end)-[:DEPENDS_ON]->()  // End has no dependencies
AND NOT ()-[:DEPENDS_ON]->(start)  // Start is not depended upon in this path
WITH path, length(path) AS pathLength
ORDER BY pathLength DESC
LIMIT 10
RETURN [n IN nodes(path) | n.name] AS dependencyChain,
       pathLength;

// ================================================
// 6. UTILITY QUERIES
// ================================================

// Get project overview
MATCH (p:Project {projectId: $projectId})
OPTIONAL MATCH (p)-[:CONTAINS]->(m:Module)
OPTIONAL MATCH (p)-[:CONTAINS*]->(c:Class)
OPTIONAL MATCH (p)-[:CONTAINS*]->(f:Function)
RETURN p.name AS project,
       count(DISTINCT m) AS modules,
       count(DISTINCT c) AS classes,
       count(DISTINCT f) AS functions;

// Find orphaned nodes (not connected to any project)
MATCH (n)
WHERE NOT (n:Project) AND NOT ()-[:CONTAINS*]->(n)
RETURN labels(n) AS nodeType,
       count(n) AS count;

// Delete all data for a project
MATCH (p:Project {projectId: $projectId})
OPTIONAL MATCH (p)-[:CONTAINS*0..]->(child)
DETACH DELETE p, child;
