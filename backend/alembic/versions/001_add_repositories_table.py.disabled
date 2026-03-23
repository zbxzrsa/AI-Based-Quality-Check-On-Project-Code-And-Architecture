"""Add repositories table

Revision ID: 001_repositories
Revises: 
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_repositories'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create repositories table"""
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repository_url', sa.String(500), nullable=False),
        sa.Column('owner', sa.String(255), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('branch', sa.String(255), nullable=False, server_default='main'),
        sa.Column('version', sa.String(100), nullable=True),
        sa.Column(
            'status',
            sa.Enum(
                'PENDING', 'VALIDATING', 'CLONING', 'ANALYZING', 
                'ACTIVE', 'FAILED', 'ARCHIVED',
                name='repositorystatus'
            ),
            nullable=False,
            server_default='PENDING',
            index=True
        ),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('auto_update', sa.Boolean, server_default='false'),
        sa.Column('last_synced', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('metadata', postgresql.JSONB, server_default='{}', nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_repositories_owner_name', 'repositories', ['owner', 'name'])
    op.create_index('idx_repositories_status', 'repositories', ['status'])
    op.create_index('idx_repositories_created_by', 'repositories', ['created_by'])
    op.create_index('idx_repositories_created_at', 'repositories', ['created_at'])


def downgrade() -> None:
    """Drop repositories table"""
    op.drop_index('idx_repositories_created_at', table_name='repositories')
    op.drop_index('idx_repositories_created_by', table_name='repositories')
    op.drop_index('idx_repositories_status', table_name='repositories')
    op.drop_index('idx_repositories_owner_name', table_name='repositories')
    op.drop_table('repositories')
    op.execute('DROP TYPE repositorystatus')
