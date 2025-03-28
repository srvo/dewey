import contextlib
import logging
import os
from datetime import datetime
from typing import Any, Dict, Iterator

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, scoped_session
from apscheduler.schedulers.background import BackgroundScheduler

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

        # Connection Health - Add periodic reconnection:
        self._last_validation = datetime.now()
        
        # Schedule periodic revalidation
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            self._revalidate_connection,
            'interval',
            minutes=5
        )
        self._scheduler.start()

    def _build_connection_string(self, config: Dict[str, Any]) -> str:
        """Enhanced connection string builder with timeout parameters"""
        return (
            f"postgresql+psycopg2://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['dbname']}"
            f"?sslmode={config['sslmode']}"
            f"&connect_timeout={config.get('connect_timeout', 10)}"
            f"&keepalives_idle={config.get('keepalives_idle', 30)}"
        )

    def _create_postgres_engine(self):
        """Create PostgreSQL engine using SQLAlchemy with env var support."""
        try:
            # Check for direct database URL in environment
            if "DATABASE_URL" in os.environ:
                self.logger.debug("Using DATABASE_URL from environment")
                engine = create_engine(
                    os.environ["DATABASE_URL"],
                    pool_size=self.config.get("pool_min", 5),
                    max_overflow=self.config.get("pool_max", 10),
                    pool_pre_ping=True
                )
            else:
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

                connection_str = self._build_connection_string(connection_params)
            
                # SSL Handling - Add SSL certificate handling
                ssl_args = {}
                if connection_params.get("sslmode") == "verify-full":
                    ssl_args.update({
                        "sslrootcert": self.config["sslrootcert"],
                        "sslcert": self.config["sslcert"],
                        "sslkey": self.config["sslkey"]
                    })
            
                engine = create_engine(
                    connection_str,
                    connect_args=ssl_args,
                    pool_size=db_config.get('pool_min', 5),
                    max_overflow=db_config.get('pool_max', 10),
                    pool_pre_ping=True
                )

            # Connection Pooling - Add monitoring:
            @event.listens_for(engine, "checkout")
            def checkout(dbapi_conn, connection_record, connection_proxy):
                logger.debug(f"Checking out connection from pool: {id(dbapi_conn)}")

            @event.listens_for(engine, "checkin")
            def checkin(dbapi_conn, connection_record):
                logger.debug(f"Returning connection to pool: {id(dbapi_conn)}")
            
            return engine
        except KeyError as e:
            raise DatabaseConnectionError(f"Missing PostgreSQL config key: {e}")
        except Exception as e:
            raise DatabaseConnectionError(f"PostgreSQL connection failed: {str(e)}")

    def validate_connection(self):
        """Enhanced validation with schema check"""
        try:
            with self.engine.connect() as conn:
                # Check connection and schema version
                conn.execute(text("SELECT 1"))
                schema_version = conn.execute(
                    text("SELECT MAX(version) FROM schema_versions")
                ).scalar()
                logger.info(f"Schema version: {schema_version}")
        except Exception as e:
            raise DatabaseConnectionError(f"Connection validation failed: {str(e)}")

    def _revalidate_connection(self):
        """Revalidate connection every 5 minutes"""
        if (datetime.now() - self._last_validation).total_seconds() > 300:
            self.validate_connection()
            self._last_validation = datetime.now()

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
        self._scheduler.shutdown(wait=False)  # Stop the scheduler
        logger.info("PostgreSQL connection closed")

def get_connection(config: Dict[str, Any]) -> DatabaseConnection:
    """Get a configured PostgreSQL database connection."""
    return DatabaseConnection(config)
