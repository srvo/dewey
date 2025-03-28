import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from typing import Any, Dict, Union

from dewey.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Unified database connection handler for PostgreSQL and DuckDB."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engine = self._create_engine()
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        self.validate_connection()

    def _create_engine(self):
        """Create SQLAlchemy engine based on configuration."""
        engine_type = self.config.get("engine", "duckdb")
        
        if engine_type == "postgres":
            return self._create_postgres_engine()
        return self._create_duckdb_engine()

    def _create_postgres_engine(self):
        """Create PostgreSQL engine using SQLAlchemy."""
        try:
            db_config = self.config["postgres"]
            connection_str = (
                f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
            )
            return create_engine(
                connection_str,
                pool_size=db_config.get("pool_min", 5),
                max_overflow=db_config.get("pool_max", 10),
                pool_pre_ping=True
            )
        except KeyError as e:
            raise DatabaseConnectionError(f"Missing PostgreSQL config key: {e}")
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(f"PostgreSQL connection failed: {str(e)}")

    def _create_duckdb_engine(self):
        """Create DuckDB engine using SQLAlchemy."""
        try:
            db_config = self.config["duckdb"]
            connection_str = f"duckdb:///{db_config['local_path']}"
            return create_engine(connection_str)
        except KeyError as e:
            raise DatabaseConnectionError(f"Missing DuckDB config key: {e}")
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(f"DuckDB connection failed: {str(e)}")

    def validate_connection(self):
        """Validate the database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info(f"Connected to {self.config.get('engine', 'duckdb').upper()}")
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(f"Connection validation failed: {str(e)}")

    def get_session(self):
        """Get a new scoped database session."""
        return self.Session()

    def close(self):
        """Close all connections and cleanup resources."""
        self.Session.remove()
        self.engine.dispose()
        logger.info("Database connection closed")

def get_connection(config: Dict[str, Any]) -> DatabaseConnection:
    """Get a configured database connection.
    
    Args:
        config: Database configuration dictionary from dewey.yaml
    
    Returns:
        Initialized DatabaseConnection instance
    """
    return DatabaseConnection(config)
