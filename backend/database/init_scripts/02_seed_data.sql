-- ================================================
-- Sample Seed Data for AI Code Review Platform
-- ================================================

-- Insert sample users
INSERT INTO users (id, email, password_hash, role, full_name) VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqRJSm9T8u', 'admin', 'Admin User'),
    ('b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'developer@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqRJSm9T8u', 'developer', 'John Developer'),
    ('c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'reviewer@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqRJSm9T8u', 'reviewer', 'Jane Reviewer'),
    ('d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'compliance@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqRJSm9T8u', 'compliance_officer', 'Bob Compliance'),
    ('e4eebc99-9c0b-4ef8-bb6d-6bb9bd380a55', 'manager@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqRJSm9T8u', 'manager', 'Alice Manager')
ON CONFLICT (id) DO NOTHING;

-- Insert sample projects
INSERT INTO projects (id, owner_id, name, description, github_repo_url, language) VALUES
    ('f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'E-Commerce Platform', 'Microservices-based e-commerce platform', 'https://github.com/example/ecommerce', 'Python'),
    ('g6eebc99-9c0b-4ef8-bb6d-6bb9bd380a77', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Mobile Banking App', 'React Native banking application', 'https://github.com/example/banking-app', 'TypeScript'),
    ('h7eebc99-9c0b-4ef8-bb6d-6bb9bd380a88', 'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'Data Analytics Pipeline', 'Real-time data processing pipeline', 'https://github.com/example/analytics', 'Python')
ON CONFLICT (id) DO NOTHING;

-- Insert sample pull requests
INSERT INTO pull_requests (id, project_id, github_pr_number, title, description, author_id, status, risk_score, branch_name, commit_sha, files_changed, lines_added, lines_deleted) VALUES
    ('i8eebc99-9c0b-4ef8-bb6d-6bb9bd380a99', 'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66', 101, 'Add payment processing module', 'Implements Stripe payment integration', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'reviewed', 0.65, 'feature/payment', 'abc123def456', 12, 450, 80),
    ('j9eebc99-9c0b-4ef8-bb6d-6bb9bd380aaa', 'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66', 102, 'Update authentication logic', 'Refactor JWT authentication', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'analyzing', 0.45, 'feature/auth-refactor', 'def456ghi789', 8, 230, 150),
    ('k0eebc99-9c0b-4ef8-bb6d-6bb9bd380bbb', 'g6eebc99-9c0b-4ef8-bb6d-6bb9bd380a77', 201, 'Fix memory leak in transactions', 'Resolves memory leak issue', 'c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'approved', 0.25, 'fix/memory-leak', 'ghi789jkl012', 3, 45, 32),
    ('l1eebc99-9c0b-4ef8-bb6d-6bb9bd380ccc', 'h7eebc99-9c0b-4ef8-bb6d-6bb9bd380a88', 301, 'Add Kafka integration', 'Implements Kafka event streaming', 'b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'pending', 0.75, 'feature/kafka', 'jkl012mno345', 15, 680, 20)
ON CONFLICT (id) DO NOTHING;

-- Insert sample review results
INSERT INTO review_results (id, pull_request_id, ai_suggestions, architectural_impact, security_issues, compliance_status, confidence_score, total_issues, critical_issues) VALUES
    ('m2eebc99-9c0b-4ef8-bb6d-6bb9bd380ddd',
     'i8eebc99-9c0b-4ef8-bb6d-6bb9bd380a99',
     '{
        "suggestions": [
            {"type": "security", "severity": "high", "message": "Consider input validation for payment amounts", "line": 45},
            {"type": "performance", "severity": "medium", "message": "Use async payment processing", "line": 78},
            {"type": "best_practice", "severity": "low", "message": "Add error logging", "line": 120}
        ]
     }'::jsonb,
     '{
        "impact_level": "moderate",
        "affected_modules": ["payment", "order"],
        "new_dependencies": ["stripe"],
        "coupling_increase": 0.15
     }'::jsonb,
     '{
        "issues": [
            {"type": "input_validation", "severity": "high", "cwe": "CWE-20", "description": "Missing input validation"}
        ],
        "security_score": 0.7
     }'::jsonb,
     '{
        "pci_compliant": false,
        "gdpr_compliant": true,
        "issues": ["PCI DSS requirement 6.5.1 - Input validation needed"]
     }'::jsonb,
     0.85,
     3,
     1),
    ('n3eebc99-9c0b-4ef8-bb6d-6bb9bd380eee',
     'k0eebc99-9c0b-4ef8-bb6d-6bb9bd380bbb',
     '{
        "suggestions": [
            {"type": "code_quality", "severity": "low", "message": "Consider using WeakMap for caching", "line": 23}
        ]
     }'::jsonb,
     '{
        "impact_level": "low",
        "affected_modules": ["transaction"],
        "coupling_increase": 0.02
     }'::jsonb,
     '{
        "issues": [],
        "security_score": 0.95
     }'::jsonb,
     '{
        "pci_compliant": true,
        "gdpr_compliant": true,
        "issues": []
     }'::jsonb,
     0.92,
     1,
     0)
ON CONFLICT (id) DO NOTHING;

-- Insert sample audit logs
INSERT INTO audit_logs (user_id, action, entity_type, entity_id, changes, ip_address) VALUES
    ('b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'create', 'pull_request', 'i8eebc99-9c0b-4ef8-bb6d-6bb9bd380a99', '{"title": "Add payment processing module"}'::jsonb, '192.168.1.100'),
    ('c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'approve', 'pull_request', 'k0eebc99-9c0b-4ef8-bb6d-6bb9bd380bbb', '{"status": "approved", "reviewer_comment": "LGTM"}'::jsonb, '192.168.1.101'),
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'update', 'project', 'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66', '{"is_active": true}'::jsonb, '192.168.1.102');

-- Insert sample architectural baselines
INSERT INTO architectural_baselines (id, project_id, version, description, graph_snapshot, metrics, commit_sha, is_current) VALUES
    ('o4eebc99-9c0b-4ef8-bb6d-6bb9bd380fff',
     'f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66',
     'v1.0.0',
     'Initial architecture baseline',
     '{
        "nodes": 45,
        "edges": 128,
        "modules": ["auth", "payment", "order", "user"],
        "layers": ["api", "service", "data"]
     }'::jsonb,
     '{
        "complexity": 0.45,
        "coupling": 0.32,
        "cohesion": 0.78,
        "maintainability_index": 75.5
     }'::jsonb,
     'baseline001',
     true),
    ('p5eebc99-9c0b-4ef8-bb6d-6bb9bd381000',
     'g6eebc99-9c0b-4ef8-bb6d-6bb9bd380a77',
     'v1.0.0',
     'Initial mobile app baseline',
     '{
        "nodes": 32,
        "edges": 89,
        "modules": ["auth", "transactions", "ui"],
        "layers": ["presentation", "business", "data"]
     }'::jsonb,
     '{
        "complexity": 0.38,
        "coupling": 0.28,
        "cohesion": 0.82,
        "maintainability_index": 82.3
     }'::jsonb,
     'baseline002',
     true)
ON CONFLICT (id) DO NOTHING;

-- Useful queries for verification
-- SELECT * FROM active_pull_requests;
-- SELECT * FROM project_statistics;
-- SELECT email, role, created_at FROM users;
