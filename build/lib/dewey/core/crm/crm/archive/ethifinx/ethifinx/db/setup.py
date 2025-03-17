from pathlib import Path
import os
from dotenv import load_dotenv
import duckdb
from db import DB_PATH, DATA_DIR

# Load environment variables
load_dotenv()

# Setup paths
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "/Users/srvo/notebooks"))
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "research.db"
SCHEMA_DIR = DATA_DIR / "schema_versions"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SCHEMA_DIR.mkdir(parents=True, exist_ok=True)


def setup_database():
    """Initialize the database with basic schema"""
    print(f"Creating database at: {DB_PATH}")

    conn = duckdb.connect(str(DB_PATH))

    try:
        # Schema version tracking
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                version_id VARCHAR PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """
        )

        # Companies table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name VARCHAR UNIQUE,
                industry VARCHAR,
                headquarters VARCHAR,
                description TEXT,
                website VARCHAR,
                founded VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Research findings table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_findings (
                id INTEGER PRIMARY KEY,
                company_id INTEGER,
                category VARCHAR,
                summary TEXT,
                source VARCHAR,
                url VARCHAR,
                relevance_score FLOAT,
                raw_data JSON,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """
        )

        # Search queries table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS search_queries (
                id INTEGER PRIMARY KEY,
                company_id INTEGER,
                category VARCHAR,
                query_text TEXT,
                source_type VARCHAR,
                parameters JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """
        )

        # News articles table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY,
                company_id INTEGER,
                title VARCHAR,
                url VARCHAR UNIQUE,
                source VARCHAR,
                published_date TIMESTAMP,
                content TEXT,
                sentiment FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """
        )

        # Record schema version
        conn.execute(
            """
            INSERT INTO schema_versions (version_id, description)
            VALUES (?, ?)
            ON CONFLICT (version_id) DO NOTHING
        """,
            ("1.0", "Initial schema with companies, findings, queries, and news"),
        )

        # Test insert
        conn.execute(
            """
            INSERT INTO companies (id, name, industry) 
            VALUES (1, 'Test Corp', 'Technology')
            ON CONFLICT (name) DO NOTHING
        """
        )

        # Verify
        result = conn.execute("SELECT * FROM companies").fetchall()
        print("\nDatabase created successfully!")
        print("Test query result:", result)

    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    setup_database()
