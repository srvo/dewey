import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dewey.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Main database connection class for PostgreSQL."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.engine = self._create_engine()
        self.Session = sessionmaker(bind=self.engine)

    def _create_engine(self):
        """Create SQLAlchemy engine using environment variable."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise DatabaseConnectionError("DATABASE_URL not found in environment")
            
        return create_engine(database_url)

    def get_session(self):
        """Get a new database session."""
        return self.Session()

    def close(self) -> None:
        """Close the engine."""
        self.engine.dispose()

    def execute_query(self, query: str, params: tuple = None):
        """Execute a SQL query and return results."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(query, params or ())
                return result.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise DatabaseConnectionError(f"Query failed: {e}")

# Singleton instance
db_manager = DatabaseConnection()
