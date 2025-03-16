# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""Database initialization script.

Creates all necessary database tables if they don't exist.
"""

from sqlalchemy import create_engine

from .data_store import init_db
from .models import Base


def init_database(database_url: str = "sqlite:///research.db") -> None:
    """Initialize the database and create all tables.

    Args:
    ----
        database_url: Database URL to connect to

    """
    # Initialize the database connection
    init_db(database_url)

    # Create all tables
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_database()
