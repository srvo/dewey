# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""Import TICK history from CSV file.

Imports historical TICK data from the CSV file into the database.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine

from .data_store import get_connection, init_db
from .models import Base, TickHistory


def parse_tick_value(value: str) -> int | None:
    """Parse a TICK value from string.

    Args:
    ----
        value: String value to parse

    Returns:
    -------
        Integer TICK value or None if invalid

    """
    value = value.strip()
    if not value or value == "PORT":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def import_tick_history(
    csv_path: str,
    database_url: str = "sqlite:///data/research.db",
) -> None:
    """Import TICK history from CSV file.

    Args:
    ----
        csv_path: Path to the CSV file
        database_url: Database URL to connect to

    """
    # Initialize database connection
    init_db(database_url)

    # Create engine and ensure table exists
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    success_count = 0
    error_count = 0

    with get_connection() as session:
        # Read and import CSV data
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row["Ticker"] or not row["New Tick"]:
                    continue

                # Parse date
                date_str = row["Date"].strip()
                try:
                    date = datetime.strptime(date_str, "%m/%d/%y %H:%M")
                except ValueError:
                    error_count += 1
                    continue

                # Create tick history entry
                tick_entry = TickHistory(
                    ticker=row["Ticker"].strip(),
                    date=date,
                    old_tick=parse_tick_value(row["Old Tick"]),
                    new_tick=parse_tick_value(row["New Tick"]),
                    note=f"Imported from historical data - {row.get('Month')}/{row.get('Year')}",
                )

                try:
                    session.add(tick_entry)
                    session.commit()
                    success_count += 1
                except Exception:
                    session.rollback()
                    error_count += 1
                    continue


if __name__ == "__main__":
    csv_path = Path(__file__).parent.parent / "data" / "Port 4.5 - Tick History-2.csv"
    import_tick_history(str(csv_path))
