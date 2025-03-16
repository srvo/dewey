
Revision ID: 20231123_01
Revises: 
Create Date: 2023-11-23 12:00:00.000000

"""
jls_extract_var
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
import enum

# revision identifiers, used by Alembic.
revision = '20231123_01'
down_revision = None
branch_labels = None
depends_on = None

# Enums
class EntityType(enum.Enum):
    COMPANY = "COMPANY"
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PRODUCT = "PRODUCT"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    DATA_SOURCE = "DATA_SOURCE"
    EXCLUSION_CRITERIA = "EXCLUSION_CRITERIA"

class DataSourceType(enum.Enum):
    ESG_PROVIDER = "ESG_PROVIDER"
    RESEARCH_FIRM = "RESEARCH_FIRM"
    NEWS_OUTLET = "NEWS_OUTLET"
    REGULATORY_BODY = "REGULATORY_BODY"
    NGO = "NGO"
    INTERNAL = "INTERNAL"
    OTHER = "OTHER"

def upgrade():
    # Drop existing enums if they exist
    op.execute('DROP TYPE IF EXISTS entitytype CASCADE')
    op.execute('DROP TYPE IF EXISTS datasourcetype CASCADE')
    
    # Create entity_type enum
    op.execute("CREATE TYPE entitytype AS ENUM " + str(tuple(e.value for e in EntityType)))
    op.execute("CREATE TYPE datasourcetype AS ENUM " + str(tuple(e.value for e in DataSourceType)))
    
    # Create entities table
    op.create_table(
        'entities',
        Column('id', Integer, primary_key=True),
        Column('type', Enum(EntityType, name='entitytype'), nullable=False),
        Column('name', String(255), nullable=False),
        Column('identifier', String(50), unique=True),
        Column('meta_data', JSON),
        Column('created_at', DateTime, server_default=sa.func.now()),
        Column('updated_at', DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create relationship_types table
    op.create_table(
        'relationship_types',
        Column('id', Integer, primary_key=True),
        Column('name', String(100), nullable=False, unique=True),
        Column('description', Text),
        Column('bidirectional', Boolean, default=False),
        Column('meta_data_schema', JSON)
    )
    
    # Create entity_relationships table
    op.create_table(
        'entity_relationships',
        Column('source_id', Integer, ForeignKey('entities.id'), primary_key=True),
        Column('target_id', Integer, ForeignKey('entities.id'), primary_key=True),
        Column('relationship_type_id', Integer, ForeignKey('relationship_types.id'), primary_key=True),
        Column('strength', Float),
        Column('start_date', DateTime),
        Column('end_date', DateTime),
        Column('meta_data', JSON)
    )
    
    # Create entity_attributes table
    op.create_table(
        'entity_attributes',
        Column('id', Integer, primary_key=True),
        Column('entity_id', Integer, ForeignKey('entities.id'), nullable=False),
        Column('name', String(100), nullable=False),
        Column('value', Text),
        Column('value_type', String(50)),
        Column('timestamp', DateTime, server_default=sa.func.now())
    )
    
    # Create events table
    op.create_table(
        'events',
        Column('id', Integer, primary_key=True),
        Column('entity_id', Integer, ForeignKey('entities.id'), nullable=False),
        Column('event_type', String(100), nullable=False),
        Column('timestamp', DateTime, nullable=False),
        Column('description', Text),
        Column('meta_data', JSON),
        Column('source_id', Integer, ForeignKey('entities.id')),
        Column('confidence', Float)
    )
    
    # Create assessments table
    op.create_table(
        'assessments',
        Column('id', Integer, primary_key=True),
        Column('entity_id', Integer, ForeignKey('entities.id'), nullable=False),
        Column('source_id', Integer, ForeignKey('entities.id'), nullable=False),
        Column('assessment_type', String(100), nullable=False),
        Column('timestamp', DateTime, nullable=False, server_default=sa.func.now()),
        Column('value', Text),
        Column('meta_data', JSON),
        Column('confidence', Float),
        Column('valid_from', DateTime),
        Column('valid_until', DateTime),
        Column('superseded_by_id', Integer, ForeignKey('assessments.id'))
    )
    
    # Migrate existing company data
    op.execute("""
        INSERT INTO entities (type, name, identifier, meta_data, created_at, updated_at)
        SELECT 'COMPANY', name, ticker, 
            json_build_object(
                'category', category,
                'sector', sector,
                'current_tick', current_tick,
                'last_review', last_review,
                'rss_feed', rss_feed,
                'isin', isin
            ),
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM companies
    """)
    
    # Create indexes
    op.create_index('idx_entities_type', 'entities', ['type'])
    op.create_index('idx_entities_identifier', 'entities', ['identifier'])
    op.create_index('idx_entity_relationships_source', 'entity_relationships', ['source_id'])
    op.create_index('idx_entity_relationships_target', 'entity_relationships', ['target_id'])
    op.create_index('idx_events_entity', 'events', ['entity_id'])
    op.create_index('idx_events_timestamp', 'events', ['timestamp'])
    op.create_index('idx_assessments_entity', 'assessments', ['entity_id'])
    op.create_index('idx_assessments_source', 'assessments', ['source_id'])
    op.create_index('idx_assessments_valid', 'assessments', ['valid_from', 'valid_until'])

def downgrade():
    # Drop indexes
    op.drop_index('idx_assessments_valid')
    op.drop_index('idx_assessments_source')
    op.drop_index('idx_assessments_entity')
    op.drop_index('idx_events_timestamp')
    op.drop_index('idx_events_entity')
    op.drop_index('idx_entity_relationships_target')
    op.drop_index('idx_entity_relationships_source')
    op.drop_index('idx_entities_identifier')
    op.drop_index('idx_entities_type')
    
    # Drop tables
    op.drop_table('assessments')
    op.drop_table('events')
    op.drop_table('entity_attributes')
    op.drop_table('entity_relationships')
    op.drop_table('relationship_types')
    op.drop_table('entities')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS entitytype CASCADE')
    op.execute('DROP TYPE IF EXISTS datasourcetype CASCADE')
