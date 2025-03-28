import contextlib
import logging
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from typing import Any, Dict, Iterator

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
        """Create PostgreSQL engine using SQLAlchemy with env var support."""
        try:
            # Check for direct database URL in environment
            if "DATABASE_URL" in os.environ:
                self.logger.debug("Using DATABASE_URL from environment")
                return create_engine(
                    os.environ["DATABASE_URL"],
                    pool_size=self.config.get("pool_min", 5),
                    max_overflow=self.config.get("pool_max", 10),
                    pool_pre_ping=True
                )

            # Build from environment variables with config fallbacks
            db_config = self.config.get("postgres", {})
            connection_params = {
                'host': os.getenv('POSTGRES_HOST', db_config.get('host')),
                'port': os.getenv('POSTGRES_PORT', db_config.get('port', 5432)),
                'dbname': os.getenv('POSTGRES_DB', db_config.get('dbname')),
                'user': os.getenv('POSTGRES_USER', db_config.get('user')),
                'password': os.getenv('POSTGRES_PASSWORD', db_config.get('password')),
                'sslmode': os.getenv('POSTGRES_SSLMODE', db_config.get('sslmode', 'prefer'))
            }

            # Validate required parameters
            required = ['host', 'dbname', 'user', 'password']
            missing = [field for field in required if not connection_params[field]]
            if missing:
                raise DatabaseConnectionError(
                    f"Missing PostgreSQL config: {', '.join(missing)}. "
                    "Set via environment variables or config file."
                )

            connection_str = (
                f"postgresql+psycopg2://"
                f"{connection_params['user']}:{connection_params['password']}"
                f"@{connection_params['host']}:{connection_params['port']}"
                f"/{connection_params['dbname']}"
                f"?sslmode={connection_params['sslmode']}"
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

    @contextlib.contextmanager
    def get_session(self) -> Iterator[scoped_session]:
        """Get a database session context manager."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database operation failed: {str(e)}")
            raise DatabaseConnectionError(str(e)) from e
        finally:
            session.close()

    def close(self):
        """Close all connections and cleanup resources."""
        self.Session.remove()
        self.engine.dispose()
        logger.info("PostgreSQL connection closed")

def get_connection(config: Dict[str, Any]) -> DatabaseConnection:
    """Get a configured PostgreSQL database connection."""
    return DatabaseConnection(config)
