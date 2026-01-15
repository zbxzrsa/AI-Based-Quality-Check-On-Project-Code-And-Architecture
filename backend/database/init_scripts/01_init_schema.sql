-- ================================================
-- AI Code Review Platform - PostgreSQL Schema
-- Complete database schema with all required tables
-- ================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ================================================
-- ENUMS
-- ================================================

-- User roles
CREATE TYPE user_role AS ENUM (
    'admin',
    'developer',
    'reviewer',
    'compliance_officer',
    'manager'
);

-- Pull request status
CREATE TYPE pr_status AS ENUM (
    'pending',
    'analyzing',
    'reviewed',
    'approved',
    'rejected'
);

-- Audit action types
CREATE TYPE audit_action AS ENUM (
    'create',
    'update',
    'delete',
    'approve',
    'reject'
);

-- ================================================
-- TABLE: users
-- ================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'developer',
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for users table
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- ================================================
-- TABLE: projects
-- ================================================

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    github_repo_url VARCHAR(500) UNIQUE,
    github_webhook_secret VARCHAR(255),
    language VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for projects table
CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_github_url ON projects(github_repo_url);
CREATE INDEX idx_projects_is_active ON projects(is_active);
CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- ================================================
-- TABLE: pull_requests
-- ================================================

CREATE TABLE IF NOT EXISTS pull_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    github_pr_number INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    author_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status pr_status NOT NULL DEFAULT 'pending',
    risk_score FLOAT CHECK (risk_score >= 0 AND risk_score <= 1),
    branch_name VARCHAR(255),
    commit_sha VARCHAR(40),
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMP WITH TIME ZONE,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, github_pr_number)
);

-- Indexes for pull_requests table
CREATE INDEX idx_pr_project ON pull_requests(project_id);
CREATE INDEX idx_pr_github_number ON pull_requests(github_pr_number);
CREATE INDEX idx_pr_author ON pull_requests(author_id);
CREATE INDEX idx_pr_status ON pull_requests(status);
CREATE INDEX idx_pr_risk_score ON pull_requests(risk_score DESC);
CREATE INDEX idx_pr_created_at ON pull_requests(created_at DESC);
CREATE INDEX idx_pr_project_status ON pull_requests(project_id, status);

-- ================================================
-- TABLE: review_results
-- ================================================

CREATE TABLE IF NOT EXISTS review_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pull_request_id UUID NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    ai_suggestions JSONB,
    architectural_impact JSONB,
    security_issues JSONB,
    compliance_status JSONB,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    total_issues INTEGER DEFAULT 0,
    critical_issues INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pull_request_id)
);

-- Indexes for review_results table
CREATE INDEX idx_review_pr ON review_results(pull_request_id);
CREATE INDEX idx_review_confidence ON review_results(confidence_score DESC);
CREATE INDEX idx_review_created_at ON review_results(created_at DESC);
-- JSONB indexes for efficient querying
CREATE INDEX idx_review_ai_suggestions ON review_results USING GIN (ai_suggestions);
CREATE INDEX idx_review_security_issues ON review_results USING GIN (security_issues);

-- ================================================
-- TABLE: audit_logs
-- ================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action audit_action NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit_logs table
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_user_timestamp ON audit_logs(user_id, timestamp DESC);
-- JSONB index for changes
CREATE INDEX idx_audit_changes ON audit_logs USING GIN (changes);

-- ================================================
-- TABLE: architectural_baselines
-- ================================================

CREATE TABLE IF NOT EXISTS architectural_baselines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    graph_snapshot JSONB NOT NULL,
    metrics JSONB,
    commit_sha VARCHAR(40),
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, version)
);

-- Indexes for architectural_baselines table
CREATE INDEX idx_baseline_project ON architectural_baselines(project_id);
CREATE INDEX idx_baseline_version ON architectural_baselines(version);
CREATE INDEX idx_baseline_is_current ON architectural_baselines(is_current);
CREATE INDEX idx_baseline_created_at ON architectural_baselines(created_at DESC);
CREATE INDEX idx_baseline_project_current ON architectural_baselines(project_id, is_current);
-- JSONB indexes
CREATE INDEX idx_baseline_graph ON architectural_baselines USING GIN (graph_snapshot);
CREATE INDEX idx_baseline_metrics ON architectural_baselines USING GIN (metrics);

-- ================================================
-- TRIGGERS
-- ================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at column
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to ensure only one current baseline per project
CREATE OR REPLACE FUNCTION ensure_single_current_baseline()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_current = TRUE THEN
        UPDATE architectural_baselines
        SET is_current = FALSE
        WHERE project_id = NEW.project_id AND id != NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_single_current_baseline
    BEFORE INSERT OR UPDATE ON architectural_baselines
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_current_baseline();

-- ================================================
-- VIEWS
-- ================================================

-- View for active pull requests with review status
CREATE OR REPLACE VIEW active_pull_requests AS
SELECT 
    pr.id,
    pr.project_id,
    p.name AS project_name,
    pr.github_pr_number,
    pr.title,
    pr.author_id,
    u.email AS author_email,
    u.full_name AS author_name,
    pr.status,
    pr.risk_score,
    rr.confidence_score,
    rr.total_issues,
    rr.critical_issues,
    pr.created_at,
    pr.analyzed_at,
    pr.reviewed_at
FROM pull_requests pr
JOIN projects p ON pr.project_id = p.id
LEFT JOIN users u ON pr.author_id = u.id
LEFT JOIN review_results rr ON pr.id = rr.pull_request_id
WHERE pr.status IN ('pending', 'analyzing', 'reviewed');

-- View for project statistics
CREATE OR REPLACE VIEW project_statistics AS
SELECT 
    p.id AS project_id,
    p.name AS project_name,
    COUNT(DISTINCT pr.id) AS total_pull_requests,
    COUNT(DISTINCT CASE WHEN pr.status = 'approved' THEN pr.id END) AS approved_prs,
    COUNT(DISTINCT CASE WHEN pr.status = 'rejected' THEN pr.id END) AS rejected_prs,
    AVG(pr.risk_score) AS avg_risk_score,
    AVG(rr.confidence_score) AS avg_confidence_score,
    SUM(rr.total_issues) AS total_issues_found,
    SUM(rr.critical_issues) AS total_critical_issues
FROM projects p
LEFT JOIN pull_requests pr ON p.id = pr.project_id
LEFT JOIN review_results rr ON pr.id = rr.pull_request_id
WHERE p.is_active = TRUE
GROUP BY p.id, p.name;

-- ================================================
-- INITIAL DATA COMMENTS
-- ================================================

COMMENT ON TABLE users IS 'User accounts with role-based access control';
COMMENT ON TABLE projects IS 'GitHub projects integrated with the platform';
COMMENT ON TABLE pull_requests IS 'Pull requests submitted for AI review';
COMMENT ON TABLE review_results IS 'AI-generated review results with suggestions and analysis';
COMMENT ON TABLE audit_logs IS 'Audit trail for all system actions';
COMMENT ON TABLE architectural_baselines IS 'Historical snapshots of project architecture';

COMMENT ON COLUMN pull_requests.risk_score IS 'AI-calculated risk score (0-1, higher is riskier)';
COMMENT ON COLUMN review_results.confidence_score IS 'AI confidence in review results (0-1)';
COMMENT ON COLUMN architectural_baselines.is_current IS 'Flag indicating the current baseline version';
