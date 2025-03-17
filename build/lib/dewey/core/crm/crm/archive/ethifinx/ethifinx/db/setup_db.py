import sqlite3
from pathlib import Path

# Setup database path
DATABASE_PATH = Path("/Users/srvo/notebooks/data/research.db")


def setup_database():
    """Create research database tables if they don't exist"""
    # Ensure the data directory exists
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Create database connection
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Create universe table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS universe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ticker TEXT NOT NULL UNIQUE,
                isin TEXT,
                security_type TEXT,
                market_cap REAL,
                sector TEXT,
                industry TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()
        print("Database tables created successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    setup_database()
