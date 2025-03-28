import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from typing import Any, Dict

from dewey.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """SQLAlchemy-based database connection handler for PostgreSQL."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = self._create_postgres_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        self.Session = scoped_session(self.SessionLocal)
        self.validate_connection()

    def _create_postgres_engine(self):
        """Create SQLAlchemy engine for PostgreSQL."""
        try:
            db_config = self.config["postgres"]
            connection_str = (
                f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
            )
            return create_engine(
                connection_str,
                pool_size=db_config.get('pool_min', 5),
                max_overflow=db_config.get('pool_max', 10),
                pool_pre_ping=True
            )
        except KeyError as e:
            raise DatabaseConnectionError(f"Missing PostgreSQL config key: {e}")
        except Exception as e:
            raise DatabaseConnectionError(f"PostgreSQL connection failed: {str(e)}")

    def validate_connection(self):
        """Validate the database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL connection validated")
        except Exception as e:
            raise DatabaseConnectionError(f"Connection validation failed: {str(e)}")

    def get_session(self):
        """Get a new scoped database session."""
        return self.Session()

    def close(self):
        """Close all connections and cleanup resources."""
        self.Session.remove()
        self.engine.dispose()
        logger.info("PostgreSQL connection closed")

def get_connection(config: Dict[str, Any]) -> DatabaseConnection:
    """Get a configured PostgreSQL database connection."""
    return DatabaseConnection(config)
