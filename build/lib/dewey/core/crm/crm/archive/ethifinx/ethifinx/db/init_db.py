"""Database initialization script.

Creates all necessary database tables if they don't exist.
"""

from sqlalchemy import create_engine
from .models import Base
from .data_store import init_db, get_connection


def init_database(database_url: str = "sqlite:///research.db"):
    """Initialize the database and create all tables.
    
    Args:
        database_url: Database URL to connect to
    """
    # Initialize the database connection
    init_db(database_url)
    
    # Create all tables
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_database() 