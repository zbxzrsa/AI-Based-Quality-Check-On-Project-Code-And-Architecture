"""Improve user management and project invitation system

Revision ID: 004_improve_user_management
Revises: 003_add_audit_tables
Create Date: 2026-03-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_improve_user_management'
down_revision = '003_add_audit_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema for improved user management and project invitations"""
    
    # Add essential columns to users table
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('account_locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verification_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for user management
    op.create_index('ix_users_email_verification_token', 'users', ['email_verification_token'])
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'])
    op.create_index('ix_users_last_login', 'users', ['last_login'])
    
    # Create project invitations table for invitation-based access control
    op.create_table('project_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('inviter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invitee_email', sa.String(255), nullable=False),
        sa.Column('invitee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('invitation_token', sa.String(255), nullable=False, unique=True),
        sa.Column('role', sa.String(50), nullable=False, default='member'),  # member, maintainer
        sa.Column('status', sa.String(20), nullable=False, default='pending'),  # pending, accepted, declined, expired
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for project invitations
    op.create_index('ix_project_invitations_project_id', 'project_invitations', ['project_id'])
    op.create_index('ix_project_invitations_invitee_email', 'project_invitations', ['invitee_email'])
    op.create_index('ix_project_invitations_invitation_token', 'project_invitations', ['invitation_token'])
    op.create_index('ix_project_invitations_status', 'project_invitations', ['status'])
    op.create_index('ix_project_invitations_expires_at', 'project_invitations', ['expires_at'])
    
    # Create project members table to track project access
    op.create_table('project_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, default='member'),  # owner, maintainer, member
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('project_id', 'user_id', name='unique_project_member'),
    )
    
    # Create indexes for project members
    op.create_index('ix_project_members_project_id', 'project_members', ['project_id'])
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'])
    op.create_index('ix_project_members_role', 'project_members', ['role'])


def downgrade() -> None:
    """Downgrade database schema"""
    
    # Drop tables
    op.drop_table('project_members')
    op.drop_table('project_invitations')
    
    # Drop indexes
    op.drop_index('ix_users_last_login', 'users')
    op.drop_index('ix_users_password_reset_token', 'users')
    op.drop_index('ix_users_email_verification_token', 'users')
    
    # Drop columns from users table
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'account_locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login')