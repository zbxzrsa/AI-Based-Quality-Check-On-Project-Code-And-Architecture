"""add standards fields to findings

Revision ID: add_standards_fields
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_standards_fields'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    """Add ISO/IEC 25010, ISO/IEC 23396, and OWASP fields to review_comments and architecture_violations"""
    
    # Add standards fields to review_comments table
    op.add_column('review_comments', sa.Column('iso_25010_characteristic', sa.String(128), nullable=True))
    op.add_column('review_comments', sa.Column('iso_25010_sub_characteristic', sa.String(128), nullable=True))
    op.add_column('review_comments', sa.Column('iso_23396_practice', sa.String(128), nullable=True))
    op.add_column('review_comments', sa.Column('owasp_reference', sa.String(128), nullable=True))
    
    # Add standards fields to architecture_violations table
    op.add_column('architecture_violations', sa.Column('iso_25010_characteristic', sa.String(128), nullable=True))
    op.add_column('architecture_violations', sa.Column('iso_25010_sub_characteristic', sa.String(128), nullable=True))
    op.add_column('architecture_violations', sa.Column('iso_23396_practice', sa.String(128), nullable=True))
    op.add_column('architecture_violations', sa.Column('owasp_reference', sa.String(128), nullable=True))
    
    # Create indexes for better query performance
    op.create_index('idx_review_comments_iso25010', 'review_comments', ['iso_25010_characteristic'])
    op.create_index('idx_review_comments_iso23396', 'review_comments', ['iso_23396_practice'])
    op.create_index('idx_review_comments_owasp', 'review_comments', ['owasp_reference'])
    
    op.create_index('idx_arch_violations_iso25010', 'architecture_violations', ['iso_25010_characteristic'])
    op.create_index('idx_arch_violations_iso23396', 'architecture_violations', ['iso_23396_practice'])
    op.create_index('idx_arch_violations_owasp', 'architecture_violations', ['owasp_reference'])


def downgrade():
    """Remove standards fields from review_comments and architecture_violations"""
    
    # Drop indexes
    op.drop_index('idx_arch_violations_owasp', 'architecture_violations')
    op.drop_index('idx_arch_violations_iso23396', 'architecture_violations')
    op.drop_index('idx_arch_violations_iso25010', 'architecture_violations')
    
    op.drop_index('idx_review_comments_owasp', 'review_comments')
    op.drop_index('idx_review_comments_iso23396', 'review_comments')
    op.drop_index('idx_review_comments_iso25010', 'review_comments')
    
    # Drop columns from architecture_violations
    op.drop_column('architecture_violations', 'owasp_reference')
    op.drop_column('architecture_violations', 'iso_23396_practice')
    op.drop_column('architecture_violations', 'iso_25010_sub_characteristic')
    op.drop_column('architecture_violations', 'iso_25010_characteristic')
    
    # Drop columns from review_comments
    op.drop_column('review_comments', 'owasp_reference')
    op.drop_column('review_comments', 'iso_23396_practice')
    op.drop_column('review_comments', 'iso_25010_sub_characteristic')
    op.drop_column('review_comments', 'iso_25010_characteristic')
