"""Add code review and architecture analysis tables

Revision ID: 1a2b3c4d5e6f
Revises: <previous_migration_id>
Create Date: 2023-11-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = '<previous_migration_id>'
branch_labels = None
depends_on = None


def upgrade():
    # Create enums
    pr_status_enum = sa.Enum(
        'pending', 'analyzing', 'reviewed', 'approved', 'rejected', 'merged',
        name='prstatus',
        create_type=True
    )
    
    review_status_enum = sa.Enum(
        'pending', 'in_progress', 'completed', 'failed',
        name='reviewstatus',
        create_type=True
    )
    
    # Create tables
    op.create_table(
        'pull_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('github_pr_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('branch_name', sa.String(length=256), nullable=True),
        sa.Column('commit_sha', sa.String(length=64), nullable=True),
        sa.Column('files_changed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('lines_added', sa.Integer(), server_default='0', nullable=False),
        sa.Column('lines_deleted', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', pr_status_enum, server_default='pending', nullable=False),
        sa.Column('risk_score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('merged_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'github_pr_number', name='uq_project_pr_number')
    )
    
    op.create_index(op.f('ix_pull_requests_project_id'), 'pull_requests', ['project_id'], unique=False)
    op.create_index(op.f('ix_pull_requests_status'), 'pull_requests', ['status'], unique=False)
    
    op.create_table(
        'code_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('pull_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', review_status_enum, server_default='pending', nullable=False),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pull_request_id'], ['pull_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_code_reviews_pull_request_id'), 'code_reviews', ['pull_request_id'], unique=False)
    op.create_index(op.f('ix_code_reviews_status'), 'code_reviews', ['status'], unique=False)
    
    op.create_table(
        'review_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('review_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('rule_id', sa.String(length=128), nullable=True),
        sa.Column('rule_name', sa.String(length=256), nullable=True),
        sa.Column('suggested_fix', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['code_reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_review_comments_review_id'), 'review_comments', ['review_id'], unique=False)
    op.create_index(op.f('ix_review_comments_severity'), 'review_comments', ['severity'], unique=False)
    
    op.create_table(
        'architecture_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('pull_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', review_status_enum, server_default='pending', nullable=False),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pull_request_id'], ['pull_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_architecture_analyses_pull_request_id'), 'architecture_analyses', ['pull_request_id'], unique=False)
    op.create_index(op.f('ix_architecture_analyses_status'), 'architecture_analyses', ['status'], unique=False)
    
    op.create_table(
        'architecture_violations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('component', sa.String(length=256), nullable=False),
        sa.Column('related_component', sa.String(length=256), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('suggested_fix', sa.Text(), nullable=True),
        sa.Column('rule_id', sa.String(length=128), nullable=True),
        sa.Column('rule_name', sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['architecture_analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_architecture_violations_analysis_id'), 'architecture_violations', ['analysis_id'], unique=False)
    op.create_index(op.f('ix_architecture_violations_severity'), 'architecture_violations', ['severity'], unique=False)


def downgrade():
    # Drop tables
    op.drop_index(op.f('ix_architecture_violations_severity'), table_name='architecture_violations')
    op.drop_index(op.f('ix_architecture_violations_analysis_id'), table_name='architecture_violations')
    op.drop_table('architecture_violations')
    
    op.drop_index(op.f('ix_architecture_analyses_status'), table_name='architecture_analyses')
    op.drop_index(op.f('ix_architecture_analyses_pull_request_id'), table_name='architecture_analyses')
    op.drop_table('architecture_analyses')
    
    op.drop_index(op.f('ix_review_comments_severity'), table_name='review_comments')
    op.drop_index(op.f('ix_review_comments_review_id'), table_name='review_comments')
    op.drop_table('review_comments')
    
    op.drop_index(op.f('ix_code_reviews_status'), table_name='code_reviews')
    op.drop_index(op.f('ix_code_reviews_pull_request_id'), table_name='code_reviews')
    op.drop_table('code_reviews')
    
    op.drop_index(op.f('ix_pull_requests_status'), table_name='pull_requests')
    op.drop_index(op.f('ix_pull_requests_project_id'), table_name='pull_requests')
    op.drop_table('pull_requests')
    
    # Drop enums
    sa.Enum(name='reviewstatus').drop(op.get_bind(), checkfirst=False)
    sa.Enum(name='prstatus').drop(op.get_bind(), checkfirst=False)
