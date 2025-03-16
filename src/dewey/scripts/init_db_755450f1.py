# Formatting failed: LLM generation failed: Gemini API error: Could not acquire rate limit slot for gemini-2.0-flash after 3 attempts

#!/usr/bin/env python3

import os
from pathlib import Path

import duckdb

# Default database paths
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/Users/srvo/ethifinx"))
DEFAULT_DB_PATH = WORKSPACE_ROOT / "data" / "research.duckdb"


def init_db() -> None:
    """Initialize the research database with tables and sample data."""
    # Create data directory if it doesn't exist
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = duckdb.connect(str(DEFAULT_DB_PATH))

    # Create tables
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS current_universe (
            ticker VARCHAR PRIMARY KEY,
            security_name VARCHAR NOT NULL,
            tick INTEGER
        )
    """,
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tick_history (
            id INTEGER PRIMARY KEY,
            ticker VARCHAR NOT NULL,
            old_tick INTEGER,
            new_tick INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            note TEXT,
            updated_by TEXT
        )
    """,
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_results (
            id INTEGER PRIMARY KEY,
            ticker VARCHAR NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary TEXT,
            risk_score INTEGER,
            confidence_score INTEGER,
            recommendation TEXT,
            structured_data JSON,
            source_categories TEXT,
            meta_info JSON
        )
    """,
    )

    # Insert sample data
    conn.execute(
        """
        INSERT INTO current_universe (ticker, security_name, tick)
        VALUES
            ('AAPL', 'Apple Inc.', 3),
            ('MSFT', 'Microsoft Corporation', 2),
            ('GOOGL', 'Alphabet Inc.', 4)
        ON CONFLICT (ticker) DO NOTHING
    """,
    )

    conn.execute(
        """
        INSERT INTO tick_history (ticker, old_tick, new_tick, note, updated_by)
        VALUES
            ('AAPL', 2, 3, 'Increased environmental focus', 'system'),
            ('MSFT', 1, 2, 'Improved governance', 'system'),
            ('GOOGL', 3, 4, 'Enhanced social initiatives', 'system')
        ON CONFLICT DO NOTHING
    """,
    )

    conn.close()


if __name__ == "__main__":
    init_db()
