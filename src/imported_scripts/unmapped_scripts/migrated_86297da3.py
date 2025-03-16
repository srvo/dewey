"""Migrate existing events to new schema.

Revision ID: 20231123_02
Revises: 20231123_01
Create Date: 2023-11-23 12:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20231123_02"
down_revision = "20231123_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migrate tick history
    op.execute(
        """
        INSERT INTO events (
            entity_id,
            event_type,
            timestamp,
            meta_data,
            confidence
        )
        SELECT
            e.id as entity_id,
            'TICK',
            th.timestamp,
            json_build_object(
                'tick_value', th.tick_value,
                'moon_phase', th.moon_phase
            ),
            1.0  -- High confidence for direct market data
        FROM tick_history th
        JOIN entities e ON e.identifier = (
            SELECT ticker
            FROM companies
            WHERE companies.id = th.company_id
        )
    """,
    )

    # Migrate SEC filings
    op.execute(
        """
        INSERT INTO events (
            entity_id,
            event_type,
            timestamp,
            description,
            meta_data,
            confidence
        )
        SELECT
            e.id as entity_id,
            'SEC_FILING',
            sf.filing_date,
            'SEC Filing: ' || sf.filing_type,
            json_build_object(
                'filing_type', sf.filing_type,
                'accession_number', sf.accession_number,
                'file_number', sf.file_number,
                'url', sf.url,
                'content', sf.content,
                'content_cached', sf.content_cached
            ),
            1.0  -- High confidence for SEC filings
        FROM sec_filings sf
        JOIN entities e ON e.identifier = (
            SELECT ticker
            FROM companies
            WHERE companies.id = sf.company_id
        )
    """,
    )

    # Migrate news items
    op.execute(
        """
        INSERT INTO events (
            entity_id,
            event_type,
            timestamp,
            description,
            meta_data,
            confidence
        )
        SELECT
            e.id as entity_id,
            'NEWS',
            ni.published_date,
            ni.title,
            json_build_object(
                'url', ni.url,
                'source', ni.source,
                'content', ni.content,
                'sentiment', ni.sentiment
            ),
            CASE
                WHEN ni.sentiment IS NOT NULL THEN ABS(ni.sentiment)  -- Use sentiment as confidence if available
                ELSE 0.7  -- Default confidence for news items
            END
        FROM news_items ni
        JOIN entities e ON e.identifier = (
            SELECT ticker
            FROM companies
            WHERE companies.id = ni.company_id
        )
    """,
    )

    # Create a default internal data source for historical data
    op.execute(
        """
        INSERT INTO entities (
            type,
            name,
            identifier,
            meta_data,
            created_at,
            updated_at
        )
        VALUES (
            'DATA_SOURCE',
            'Legacy System',
            'LEGACY_INTERNAL',
            json_build_object(
                'type', 'INTERNAL',
                'description', 'Historical data from legacy system'
            ),
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
    """,
    )

    # Update all migrated events to use the legacy data source
    op.execute(
        """
        UPDATE events
        SET source_id = (
            SELECT id
            FROM entities
            WHERE identifier = 'LEGACY_INTERNAL'
        )
        WHERE source_id IS NULL
    """,
    )


def downgrade() -> None:
    # Remove events from migrated sources
    op.execute(
        """
        DELETE FROM events
        WHERE event_type IN ('TICK', 'SEC_FILING', 'NEWS')
    """,
    )

    # Remove legacy data source
    op.execute(
        """
        DELETE FROM entities
        WHERE identifier = 'LEGACY_INTERNAL'
    """,
    )
