"""Add concerned_groups, decision, and notes to exclusions table

Revision ID: 002_add_exclusion_fields
Revises: 001_initial_schema
Create Date: 2023-10-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_exclusion_fields'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('exclusions', sa.Column('concerned_groups', sa.String(), nullable=True))
    op.add_column('exclusions', sa.Column('decision', sa.String(), nullable=True))
    op.add_column('exclusions', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('exclusions', sa.Column('category', sa.String(), nullable=True))

def downgrade():
    op.drop_column('exclusions', 'concerned_groups')
    op.drop_column('exclusions', 'decision')
    op.drop_column('exclusions', 'notes')
    op.drop_column('exclusions', 'category') 