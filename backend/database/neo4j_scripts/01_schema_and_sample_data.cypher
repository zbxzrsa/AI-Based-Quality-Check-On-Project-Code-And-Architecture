// ================================================
// Neo4j Graph Database Schema
// AI Code Review Platform - Code Architecture Model
// ================================================

// ================================================
// CONSTRAINTS - Ensure unique identifiers
// ================================================

// Project constraints
CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.projectId IS UNIQUE;

// Module constraints
CREATE CONSTRAINT module_id_unique IF NOT EXISTS
FOR (m:Module) REQUIRE m.moduleId IS UNIQUE;

// Class constraints
CREATE CONSTRAINT class_id_unique IF NOT EXISTS
FOR (c:Class) REQUIRE c.classId IS UNIQUE;

// Function constraints
CREATE CONSTRAINT function_id_unique IF NOT EXISTS
FOR (f:Function) REQUIRE f.functionId IS UNIQUE;

// File constraints
CREATE CONSTRAINT file_id_unique IF NOT EXISTS
FOR (file:File) REQUIRE file.fileId IS UNIQUE;

// ================================================
// INDEXES - Optimize query performance
// ================================================

// Project indexes
CREATE INDEX project_name_idx IF NOT EXISTS FOR (p:Project) ON (p.name);
CREATE INDEX project_language_idx IF NOT EXISTS FOR (p:Project) ON (p.language);

// Module indexes
CREATE INDEX module_name_idx IF NOT EXISTS FOR (m:Module) ON (m.name);
CREATE INDEX module_path_idx IF NOT EXISTS FOR (m:Module) ON (m.path);
CREATE INDEX module_type_idx IF NOT EXISTS FOR (m:Module) ON (m.type);

// Class indexes
CREATE INDEX class_name_idx IF NOT EXISTS FOR (c:Class) ON (c.name);
CREATE INDEX class_file_path_idx IF NOT EXISTS FOR (c:Class) ON (c.filePath);

// Function indexes
CREATE INDEX function_name_idx IF NOT EXISTS FOR (f:Function) ON (f.name);
CREATE INDEX function_complexity_idx IF NOT EXISTS FOR (f:Function) ON (f.complexity);

// File indexes
CREATE INDEX file_path_idx IF NOT EXISTS FOR (file:File) ON (file.path);
CREATE INDEX file_language_idx IF NOT EXISTS FOR (file:File) ON (file.language);

// ================================================
// SAMPLE DATA - Create example graph structure
// ================================================

// Create a sample project
CREATE (p:Project {
    projectId: 'proj-001',
    name: 'E-Commerce Platform',
    language: 'Python',
    createdAt: datetime()
});

// Create modules
CREATE (m1:Module {
    moduleId: 'mod-001',
    name: 'payment',
    path: 'src/payment',
    type: 'package'
});

CREATE (m2:Module {
    moduleId: 'mod-002',
    name: 'order',
    path: 'src/order',
    type: 'package'
});

CREATE (m3:Module {
    moduleId: 'mod-003',
    name: 'user',
    path: 'src/user',
    type: 'package'
});

// Create files
CREATE (f1:File {
    fileId: 'file-001',
    path: 'src/payment/processor.py',
    language: 'Python',
    linesOfCode: 245
});

CREATE (f2:File {
    fileId: 'file-002',
    path: 'src/order/service.py',
    language: 'Python',
    linesOfCode: 189
});

// Create classes
CREATE (c1:Class {
    classId: 'class-001',
    name: 'PaymentProcessor',
    filePath: 'src/payment/processor.py',
    startLine: 15,
    endLine: 120
});

CREATE (c2:Class {
    classId: 'class-002',
    name: 'OrderService',
    filePath: 'src/order/service.py',
    startLine: 10,
    endLine: 150
});

CREATE (c3:Class {
    classId: 'class-003',
    name: 'UserManager',
    filePath: 'src/user/manager.py',
    startLine: 8,
    endLine: 95
});

// Create functions
CREATE (fn1:Function {
    functionId: 'func-001',
    name: 'process_payment',
    parameters: ['amount', 'currency', 'payment_method'],
    returnType: 'PaymentResult',
    complexity: 8
});

CREATE (fn2:Function {
    functionId: 'func-002',
    name: 'create_order',
    parameters: ['user_id', 'items', 'shipping_address'],
    returnType: 'Order',
    complexity: 12
});

CREATE (fn3:Function {
    functionId: 'func-003',
    name: 'validate_payment',
    parameters: ['payment_data'],
    returnType: 'bool',
    complexity: 5
});

// ================================================
// RELATIONSHIPS - Connect nodes
// ================================================

// Project CONTAINS modules
MATCH (p:Project {projectId: 'proj-001'})
MATCH (m1:Module {moduleId: 'mod-001'})
MATCH (m2:Module {moduleId: 'mod-002'})
MATCH (m3:Module {moduleId: 'mod-003'})
CREATE (p)-[:CONTAINS {level: 'module'}]->(m1)
CREATE (p)-[:CONTAINS {level: 'module'}]->(m2)
CREATE (p)-[:CONTAINS {level: 'module'}]->(m3);

// Module CONTAINS files
MATCH (m1:Module {moduleId: 'mod-001'})
MATCH (m2:Module {moduleId: 'mod-002'})
MATCH (f1:File {fileId: 'file-001'})
MATCH (f2:File {fileId: 'file-002'})
CREATE (m1)-[:CONTAINS {level: 'file'}]->(f1)
CREATE (m2)-[:CONTAINS {level: 'file'}]->(f2);

// File CONTAINS classes
MATCH (f1:File {fileId: 'file-001'})
MATCH (f2:File {fileId: 'file-002'})
MATCH (c1:Class {classId: 'class-001'})
MATCH (c2:Class {classId: 'class-002'})
CREATE (f1)-[:CONTAINS {level: 'class'}]->(c1)
CREATE (f2)-[:CONTAINS {level: 'class'}]->(c2);

// Class CONTAINS functions
MATCH (c1:Class {classId: 'class-001'})
MATCH (c2:Class {classId: 'class-002'})
MATCH (fn1:Function {functionId: 'func-001'})
MATCH (fn2:Function {functionId: 'func-002'})
MATCH (fn3:Function {functionId: 'func-003'})
CREATE (c1)-[:CONTAINS {level: 'method'}]->(fn1)
CREATE (c1)-[:CONTAINS {level: 'method'}]->(fn3)
CREATE (c2)-[:CONTAINS {level: 'method'}]->(fn2);

// DEPENDS_ON relationships
MATCH (m2:Module {moduleId: 'mod-002'})
MATCH (m1:Module {moduleId: 'mod-001'})
CREATE (m2)-[:DEPENDS_ON {type: 'import', weight: 0.8}]->(m1);

MATCH (m2:Module {moduleId: 'mod-002'})
MATCH (m3:Module {moduleId: 'mod-003'})
CREATE (m2)-[:DEPENDS_ON {type: 'import', weight: 0.6}]->(m3);

// CALLS relationships
MATCH (fn2:Function {functionId: 'func-002'})
MATCH (fn1:Function {functionId: 'func-001'})
CREATE (fn2)-[:CALLS {frequency: 15, callType: 'direct'}]->(fn1);

MATCH (fn1:Function {functionId: 'func-001'})
MATCH (fn3:Function {functionId: 'func-003'})
CREATE (fn1)-[:CALLS {frequency: 8, callType: 'direct'}]->(fn3);

// VIOLATES relationship example (architectural violation)
MATCH (m2:Module {moduleId: 'mod-002'})
MATCH (m1:Module {moduleId: 'mod-001'})
CREATE (m2)-[:VIOLATES {
    violationType: 'layer_violation',
    severity: 'medium',
    detectedAt: datetime(),
    description: 'Business layer directly accessing payment implementation'
}]->(m1);
