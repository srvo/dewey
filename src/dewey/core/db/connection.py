import contextlib
import logging
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import scoped_session, sessionmaker

from dewey.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """SQLAlchemy-based database connection handler for PostgreSQL."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.pg_config = config
        self.engine = self._create_postgres_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine,
        )
        self.Session = scoped_session(self.SessionLocal)
        self.validate_connection()

        # Connection Health - Add periodic reconnection:
        self._last_validation = datetime.now()

        # Schedule periodic revalidation
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(self._revalidate_connection, "interval", minutes=5)
        self._scheduler.start()

    def _build_connection_string(self, db_params: dict[str, Any]) -> str:
        """Build connection string from parameters (keys like pg_host, pg_port etc.)"""
        # Adjusted keys to match get_db_config output
        user = db_params.get("pg_user")
        password = db_params.get("pg_password")  # Might be None
        host = db_params.get("pg_host")
        port = db_params.get("pg_port")
        dbname = db_params.get("pg_dbname")
        # sslmode is not currently in get_db_config, add if needed or default
        sslmode = db_params.get("sslmode", "prefer")

        # Basic validation
        if not all([user, host, port, dbname]):
            raise ValueError("Missing required DB connection parameters in config.")

        # Handle potential None password
        password_part = f":{password}" if password else ""

        conn_str = (
            f"postgresql+psycopg2://{user}{password_part}"
            f"@{host}:{port}/{dbname}"
            f"?sslmode={sslmode}"
        )
        # Add optional timeouts if present in config (get_db_config doesn't have these)
        # conn_str += f"&connect_timeout={db_params.get('connect_timeout', 10)}"
        # conn_str += f"&keepalives_idle={db_params.get('keepalives_idle', 30)}"
        return conn_str

    def _create_postgres_engine(self):
        """Create PostgreSQL engine using SQLAlchemy with config from get_db_config."""
        try:
            # Use the pg_config directly which comes from get_db_config
            connection_params = self.pg_config

            # Validate required parameters (already done in _build_connection_string, but belt-and-suspenders)
            required = ["pg_host", "pg_port", "pg_user", "pg_dbname"]
            missing = [field for field in required if not connection_params.get(field)]
            if missing:
                raise DatabaseConnectionError(
                    f"Missing PostgreSQL config from get_db_config: {', '.join(missing)}. ",
                )

            connection_str = self._build_connection_string(connection_params)

            # SSL Handling - Adapt if ssl parameters are added to get_db_config
            ssl_args = {}
            # Example if ssl params were added:
            # if connection_params.get("sslmode") == "verify-full":
            #     ssl_args.update({
            #         "sslrootcert": connection_params["sslrootcert"],
            #         "sslcert": connection_params["sslcert"],
            #         "sslkey": connection_params["sslkey"],
            #     })

            # Get pool settings from config (get_db_config provides these)
            pool_min = connection_params.get(
                "pool_size", 5,
            )  # pool_size from get_db_config
            pool_max_overflow = 5  # Define max_overflow, not directly in get_db_config

            engine = create_engine(
                connection_str,
                connect_args=ssl_args,
                pool_size=pool_min,
                max_overflow=pool_max_overflow,
                pool_pre_ping=True,
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
            raise DatabaseConnectionError(f"PostgreSQL connection failed: {e!s}")

    def validate_connection(self):
        """Enhanced validation with schema check"""
        try:
            with self.engine.connect() as conn:
                # Check connection and schema version
                conn.execute(text("SELECT 1"))
                schema_version = conn.execute(
                    text("SELECT MAX(version) FROM schema_versions"),
                ).scalar()
                logger.info(f"Schema version: {schema_version}")
        except Exception as e:
            raise DatabaseConnectionError(f"Connection validation failed: {e!s}")

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
            logger.error(f"Database operation failed: {e!s}")
            raise DatabaseConnectionError(str(e)) from e
        finally:
            session.close()

    def close(self):
        """Close all connections and cleanup resources."""
        self.Session.remove()
        self.engine.dispose()
        self._scheduler.shutdown(wait=False)  # Stop the scheduler
        logger.info("PostgreSQL connection closed")


def get_connection(config: dict[str, Any]) -> DatabaseConnection:
    """Get a configured PostgreSQL database connection."""
    # NOTE: This might be less useful now with a global manager potentially commented out
    return DatabaseConnection(config)


# Initialize global db_manager instance using the refactored config
# --- Temporarily commented out to test import error ---
# try:
#     # Get config using the function from .config module
#     loaded_config = get_db_config()
#     db_manager = DatabaseConnection(loaded_config)
# except Exception as e:
#     logger.error(f"Failed to initialize db_manager: {e!s}")
#     db_manager = None

db_manager = None  # Explicitly set to None for now

__all__ = [
    "DatabaseConnection",
    "DatabaseConnectionError",
    "db_manager",
    "get_connection",
]
