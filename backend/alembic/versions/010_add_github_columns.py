"""Add missing GitHub connection columns to projects table

Revision ID: 010_add_github_columns
Revises: 008
Create Date: 2026-03-07

This migration adds the missing GitHub connection columns to the projects table:
- github_connection_type
- github_ssh_key_id
- github_cli_token

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_add_github_columns'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add github_connection_type column
    github_connection_type_enum = postgresql.ENUM(
        'https', 'ssh', 'cli',
        name='github_connection_type',
        create_type=False
    )
    github_connection_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('projects', sa.Column('github_connection_type', github_connection_type_enum, server_default='https', nullable=True))
    op.add_column('projects', sa.Column('github_ssh_key_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('github_cli_token', sa.String(length=500), nullable=True))

    # Add foreign key constraint for github_ssh_key_id
    op.create_foreign_key(
        'fk_projects_github_ssh_key_id',
        'projects', 'ssh_keys',
        ['github_ssh_key_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index on github_connection_type
    op.create_index('ix_projects_github_connection_type', 'projects', ['github_connection_type'])


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_projects_github_connection_type', table_name='projects')

    # Remove foreign key constraint
    op.drop_constraint('fk_projects_github_ssh_key_id', 'projects', type_='foreignkey')

    # Remove columns
    op.drop_column('projects', 'github_cli_token')
    op.drop_column('projects', 'github_ssh_key_id')
    op.drop_column('projects', 'github_connection_type')

    # Drop enum type
    sa.Enum(name='github_connection_type').drop(op.get_bind(), checkfirst=True)
