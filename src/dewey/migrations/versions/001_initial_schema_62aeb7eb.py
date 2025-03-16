# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Initial schema.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import func

# revision identifiers, used by Alembic
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create base tables
    op.create_table(
        "universe",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("ticker", sa.String, nullable=False, unique=True),
        sa.Column("isin", sa.String),
        sa.Column("security_type", sa.String),
        sa.Column("market_cap", sa.Float),
        sa.Column("sector", sa.String),
        sa.Column("industry", sa.String),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP, server_default=func.current_timestamp()),
    )

    op.create_table(
        "tick_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String, nullable=False),
        sa.Column(
            "date",
            sa.TIMESTAMP,
            server_default=func.current_timestamp(),
            nullable=False,
        ),
        sa.Column("old_tick", sa.Integer),
        sa.Column("new_tick", sa.Integer, nullable=False),
        sa.Column("note", sa.Text),
        sa.Column("updated_by", sa.String),
        sa.ForeignKeyConstraint(["ticker"], ["universe.ticker"]),
        sa.UniqueConstraint("ticker", "date", name="_ticker_date_uc"),
        sa.CheckConstraint(
            "new_tick >= -100 AND new_tick <= 100",
            name="tick_range_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("tick_history")
    op.drop_table("universe")
