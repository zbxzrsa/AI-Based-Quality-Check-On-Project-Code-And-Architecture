-- Database optimization SQL script
-- Run these optimizations for production performance

-- ================================================
-- Part 1: Index Creation
-- ================================================

-- Projects table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_owner 
  ON projects(owner_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_created 
  ON projects(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_active 
  ON projects(owner_id, is_active) 
  WHERE is_active = true;

-- Pull requests indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pr_project_status 
  ON pull_requests(project_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pr_status_created 
  ON pull_requests(status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pr_analyzed 
  ON pull_requests(analyzed_at DESC) 
  WHERE analyzed_at IS NOT NULL;

-- Review results indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_review_pr 
  ON review_results(pull_request_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_review_risk 
  ON review_results(risk_score DESC) 
  WHERE risk_score > 50;

-- Audit logs indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user_time 
  ON audit_logs(user_id, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_resource 
  ON audit_logs(resource_type, resource_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_timestamp 
  ON audit_logs(timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_event 
  ON audit_logs(event_type, timestamp DESC);

-- Users indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email 
  ON users(email) 
  WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role 
  ON users(role);

-- GIN indexes for JSONB columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_metadata_gin 
  ON projects USING gin(metadata);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_review_issues_gin 
  ON review_results USING gin(ai_suggestions);

-- ================================================
-- Part 2: Table Statistics Update
-- ================================================

ANALYZE projects;
ANALYZE pull_requests;
ANALYZE review_results;
ANALYZE audit_logs;
ANALYZE users;

-- ================================================
-- Part 3: Materialized Views
-- ================================================

-- Project statistics materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS project_stats AS
SELECT 
    p.id AS project_id,
    p.name,
    COUNT(DISTINCT pr.id) AS total_prs,
    COUNT(DISTINCT CASE WHEN pr.status = 'reviewed' THEN pr.id END) AS reviewed_prs,
    AVG(rr.risk_score) AS avg_risk_score,
    MAX(pr.created_at) AS latest_pr_date,
    COUNT(DISTINCT CASE WHEN rr.risk_score > 70 THEN pr.id END) AS high_risk_prs
FROM projects p
LEFT JOIN pull_requests pr ON p.id = pr.project_id
LEFT JOIN review_results rr ON pr.id = rr.pull_request_id
GROUP BY p.id, p.name;

CREATE UNIQUE INDEX ON project_stats(project_id);

-- Refresh materialized view (run periodically)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY project_stats;

-- ================================================
-- Part 4: Query Optimization Settings
-- ================================================

-- Connection pooling parameters
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET work_mem = '64MB';

-- Query planner
ALTER SYSTEM SET random_page_cost = 1.1;  -- For SSD
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Write-ahead log
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;

-- Parallel query
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;

-- Apply changes (requires restart):
-- SELECT pg_reload_conf();

-- ================================================
-- Part 5: Partitioning for Audit Logs
-- ================================================

-- Convert audit_logs to partitioned table (if not already)
-- This example shows monthly partitioning

-- Create partitioned table
CREATE TABLE IF NOT EXISTS audit_logs_partitioned (
    LIKE audit_logs INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create partitions for each month
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit_logs_2024_02 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Add more partitions as needed...

-- Create function to automatically create partitions
CREATE OR REPLACE FUNCTION create_audit_partition()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_date := DATE_TRUNC('month', CURRENT_DATE);
    partition_name := 'audit_logs_' || TO_CHAR(partition_date, 'YYYY_MM');
    start_date := partition_date;
    end_date := partition_date + INTERVAL '1 month';
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_logs_partitioned
         FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- Part 6: Vacuum and Maintenance
-- ================================================

-- Auto-vacuum settings for high-traffic tables
ALTER TABLE pull_requests SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

ALTER TABLE review_results SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02
);

-- ================================================
-- Part 7: Query Examples (Optimized)
-- ================================================

-- Get project with PR summary (optimized)
EXPLAIN ANALYZE
SELECT 
    p.*,
    ps.total_prs,
    ps.reviewed_prs,
    ps.avg_risk_score
FROM projects p
LEFT JOIN project_stats ps ON p.id = ps.project_id
WHERE p.id = 'project-uuid-here';

-- Get recent PRs with pagination (optimized)
EXPLAIN ANALYZE
SELECT pr.*, rr.risk_score, rr.confidence
FROM pull_requests pr
LEFT JOIN review_results rr ON pr.id = rr.pull_request_id
WHERE pr.project_id = 'project-uuid-here'
  AND pr.status = 'reviewed'
ORDER BY pr.created_at DESC
LIMIT 20 OFFSET 0;

-- Search audit logs (optimized with indexes)
EXPLAIN ANALYZE
SELECT *
FROM audit_logs
WHERE user_id = 'user-uuid-here'
  AND timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC
LIMIT 100;
