"""Complete exclusions schema with all CSV fields

Revision ID: 003_complete_exclusions_schema
Revises: 002_add_exclusion_fields
Create Date: 2024-01-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_complete_exclusions_schema'
down_revision = '002_add_exclusion_fields'
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing table if it exists
    op.drop_table('exclusions', if_exists=True)
    
    # Create complete table
    op.create_table(
        'exclusions',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('company', sa.String),
        sa.Column('ticker', sa.String, nullable=False),
        sa.Column('isin', sa.String),
        sa.Column('category', sa.String, nullable=False),  # Product-based or Conduct-based
        sa.Column('criteria', sa.String, nullable=False),  # Specific exclusion criteria
        sa.Column('concerned_groups', sa.String),
        sa.Column('decision', sa.String),
        sa.Column('excluded_date', sa.String),  # Using string as dates might be incomplete
        sa.Column('notes', sa.Text),
        sa.Column('excluded_at', sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint('ticker', name='_ticker_exclusion_uc')
    )

def downgrade():
    op.drop_table('exclusions') 