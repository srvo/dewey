"""Cleanup old tables after successful migration.

Revision ID: 20231123_03
Revises: 20231123_02
Create Date: 2023-11-23 13:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20231123_03"
down_revision = "20231123_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create backup of old tables
    op.execute("CREATE TABLE companies_backup AS SELECT * FROM companies")
    op.execute("CREATE TABLE tick_history_backup AS SELECT * FROM tick_history")
    op.execute("CREATE TABLE sec_filings_backup AS SELECT * FROM sec_filings")
    op.execute("CREATE TABLE news_items_backup AS SELECT * FROM news_items")

    # Drop old tables
    op.drop_table("news_items")
    op.drop_table("sec_filings")
    op.drop_table("tick_history")
    op.drop_table("companies")

    # Drop old enum
    op.execute("DROP TYPE IF EXISTS securitycategory")


def downgrade() -> None:
    # Recreate old tables from backups
    op.execute(
        """
        CREATE TYPE securitycategory AS ENUM (
            'CORE',
            'SATELLITE',
            'TRANSITION',
            'WATCHLIST'
        )
    """,
    )

    op.execute("CREATE TABLE companies AS SELECT * FROM companies_backup")
    op.execute("CREATE TABLE tick_history AS SELECT * FROM tick_history_backup")
    op.execute("CREATE TABLE sec_filings AS SELECT * FROM sec_filings_backup")
    op.execute("CREATE TABLE news_items AS SELECT * FROM news_items_backup")

    # Drop backup tables
    op.drop_table("companies_backup")
    op.drop_table("tick_history_backup")
    op.drop_table("sec_filings_backup")
    op.drop_table("news_items_backup")
