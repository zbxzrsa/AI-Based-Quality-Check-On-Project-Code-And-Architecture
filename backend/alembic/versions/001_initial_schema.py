"""empty message

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-14 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create custom ENUM types
    user_role_enum = postgresql.ENUM(
        'admin', 'developer', 'reviewer', 'compliance_officer', 'manager',
        name='user_role',
        create_type=False
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)
    
    pr_status_enum = postgresql.ENUM(
        'pending', 'analyzing', 'reviewed', 'approved', 'rejected',
        name='pr_status',
        create_type=False
    )
    pr_status_enum.create(op.get_bind(), checkfirst=True)
    
    audit_action_enum = postgresql.ENUM(
        'create', 'update', 'delete', 'approve', 'reject',
        name='audit_action',
        create_type=False
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False, server_default='developer'),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    op.create_index('idx_users_created_at', 'users', [sa.text('created_at DESC')])
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('github_repo_url', sa.String(length=500), nullable=True),
        sa.Column('github_webhook_secret', sa.String(length=255), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('github_repo_url')
    )
    op.create_index('idx_projects_owner', 'projects', ['owner_id'])
    op.create_index('idx_projects_github_url', 'projects', ['github_repo_url'])
    op.create_index('idx_projects_is_active', 'projects', ['is_active'])
    op.create_index('idx_projects_name', 'projects', ['name'])
    op.create_index('idx_projects_created_at', 'projects', [sa.text('created_at DESC')])
    
    # Create pull_requests table
    op.create_table(
        'pull_requests',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('github_pr_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('author_id', sa.UUID(), nullable=True),
        sa.Column('status', pr_status_enum, nullable=False, server_default='pending'),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('branch_name', sa.String(length=255), nullable=True),
        sa.Column('commit_sha', sa.String(length=40), nullable=True),
        sa.Column('files_changed', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('lines_added', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('lines_deleted', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('analyzed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint('risk_score >= 0 AND risk_score <= 1'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'github_pr_number')
    )
    op.create_index('idx_pr_project', 'pull_requests', ['project_id'])
    op.create_index('idx_pr_github_number', 'pull_requests', ['github_pr_number'])
    op.create_index('idx_pr_author', 'pull_requests', ['author_id'])
    op.create_index('idx_pr_status', 'pull_requests', ['status'])
    op.create_index('idx_pr_risk_score', 'pull_requests', [sa.text('risk_score DESC')])
    op.create_index('idx_pr_created_at', 'pull_requests', [sa.text('created_at DESC')])
    op.create_index('idx_pr_project_status', 'pull_requests', ['project_id', 'status'])
    
    # Create review_results table
    op.create_table(
        'review_results',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('pull_request_id', sa.UUID(), nullable=False),
        sa.Column('ai_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('architectural_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('security_issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('compliance_status', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('total_issues', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('critical_issues', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('confidence_score >= 0 AND confidence_score <= 1'),
        sa.ForeignKeyConstraint(['pull_request_id'], ['pull_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pull_request_id')
    )
    op.create_index('idx_review_pr', 'review_results', ['pull_request_id'])
    op.create_index('idx_review_confidence', 'review_results', [sa.text('confidence_score DESC')])
    op.create_index('idx_review_created_at', 'review_results', [sa.text('created_at DESC')])
    op.create_index('idx_review_ai_suggestions', 'review_results', ['ai_suggestions'], postgresql_using='gin')
    op.create_index('idx_review_security_issues', 'review_results', ['security_issues'], postgresql_using='gin')
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', audit_action_enum, nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_timestamp', 'audit_logs', [sa.text('timestamp DESC')])
    op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', sa.text('timestamp DESC')])
    op.create_index('idx_audit_changes', 'audit_logs', ['changes'], postgresql_using='gin')
    
    # Create architectural_baselines table
    op.create_table(
        'architectural_baselines',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('graph_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('commit_sha', sa.String(length=40), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'version')
    )
    op.create_index('idx_baseline_project', 'architectural_baselines', ['project_id'])
    op.create_index('idx_baseline_version', 'architectural_baselines', ['version'])
    op.create_index('idx_baseline_is_current', 'architectural_baselines', ['is_current'])
    op.create_index('idx_baseline_created_at', 'architectural_baselines', [sa.text('created_at DESC')])
    op.create_index('idx_baseline_project_current', 'architectural_baselines', ['project_id', 'is_current'])
    op.create_index('idx_baseline_graph', 'architectural_baselines', ['graph_snapshot'], postgresql_using='gin')
    op.create_index('idx_baseline_metrics', 'architectural_baselines', ['metrics'], postgresql_using='gin')


def downgrade() -> None:
    op.drop_table('architectural_baselines')
    op.drop_table('audit_logs')
    op.drop_table('review_results')
    op.drop_table('pull_requests')
    op.drop_table('projects')
    op.drop_table('users')
    
    # Drop ENUM types
    sa.Enum(name='audit_action').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='pr_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=True)
