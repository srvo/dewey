"""Database configuration module.

This module handles database configuration, initialization, and environment setup
for PostgreSQL databases.
"""

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables at import time to ensure variables are available
# but functions will reload them when called to ensure test mocks work
load_dotenv()

# PostgreSQL Database connection details
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", os.getenv("USER"))  # Default to system user
PG_PASSWORD = os.getenv("PG_PASSWORD")  # No default password for security
PG_DBNAME = os.getenv("PG_DBNAME", "dewey_db")

# Connection pool configuration (can be reused)
DEFAULT_POOL_SIZE = int(os.getenv("DEWEY_DB_POOL_SIZE", "5"))
MAX_RETRIES = int(os.getenv("DEWEY_DB_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("DEWEY_DB_RETRY_DELAY", "1"))

# Sync configuration (keep if still relevant, otherwise remove)
SYNC_INTERVAL = int(os.getenv("DEWEY_SYNC_INTERVAL", "21600"))  # 6 hours in seconds
MAX_SYNC_AGE = int(os.getenv("DEWEY_MAX_SYNC_AGE", "604800"))  # 7 days in seconds

# Backup configuration (adapt or remove based on PG backup strategy)
BACKUP_DIR = os.getenv("DEWEY_BACKUP_DIR", "/Users/srvo/dewey/backups")
BACKUP_RETENTION_DAYS = int(os.getenv("DEWEY_BACKUP_RETENTION_DAYS", "30"))

# Flag to indicate if running in test mode
# This will be set by tests to skip directory creation
IS_TEST_MODE = False


def get_db_config() -> dict:
    """Get database configuration.

    Returns
    -------
        Dictionary containing database configuration

    """
    # Read from environment each time to ensure we get the latest values
    # including any patched values in tests
    return {
        "pg_host": os.getenv("PG_HOST", PG_HOST),
        "pg_port": int(os.getenv("PG_PORT", str(PG_PORT))),
        "pg_user": os.getenv("PG_USER", PG_USER),
        "pg_password": os.getenv("PG_PASSWORD", PG_PASSWORD),
        "pg_dbname": os.getenv("PG_DBNAME", PG_DBNAME),
        "pool_size": int(os.getenv("DEWEY_DB_POOL_SIZE", str(DEFAULT_POOL_SIZE))),
        "max_retries": int(os.getenv("DEWEY_DB_MAX_RETRIES", str(MAX_RETRIES))),
        "retry_delay": int(os.getenv("DEWEY_DB_RETRY_DELAY", str(RETRY_DELAY))),
        "sync_interval": int(os.getenv("DEWEY_SYNC_INTERVAL", str(SYNC_INTERVAL))),
        "max_sync_age": int(os.getenv("DEWEY_MAX_SYNC_AGE", str(MAX_SYNC_AGE))),
        "backup_dir": os.getenv("DEWEY_BACKUP_DIR", BACKUP_DIR),
        "backup_retention_days": int(
            os.getenv("DEWEY_BACKUP_RETENTION_DAYS", str(BACKUP_RETENTION_DAYS)),
        ),
    }


def validate_config() -> bool:
    """Validate database configuration.

    Returns
    -------
        True if configuration is valid, False otherwise

    Raises
    ------
        Exception: If the configuration is invalid

    """
    config = get_db_config()

    # Check for necessary PostgreSQL parameters
    required_pg_params = ["pg_host", "pg_port", "pg_user", "pg_dbname"]
    missing_params = [p for p in required_pg_params if not config.get(p)]
    if missing_params:
        error_msg = "Missing required PostgreSQL config parameters: %s" % ', '.join(missing_params)
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Note: Password might be optional if using other auth methods (e.g., peer)
    # Add a check for password if it's strictly required in your setup
    # if not config.get("pg_password"):
    #     logger.warning("PostgreSQL password (PG_PASSWORD) is not set.")

    # Skip directory creation if in test mode or if backup strategy changes
    if not IS_TEST_MODE:
        try:
            # Check backup directory existence if still using file-based backups
            if config.get("backup_dir") and not os.path.exists(config["backup_dir"]):
                # Only create if backup_dir is still relevant
                # os.makedirs(config["backup_dir"])
                # logger.info(f"Created backup directory: {config['backup_dir']}")
                pass  # Decide if directory creation is needed for PG
        except (OSError, PermissionError) as e:
            logger.warning(
                "Could not create directories: %s. This is expected in test environments or if backup dir is unused.", e)

    # Check pool configuration
    if config["pool_size"] < 1:
        error_msg = "Pool size must be at least 1"
        logger.error(error_msg)
        raise Exception(error_msg)

    if config["max_retries"] < 0:
        error_msg = "Max retries must be non-negative"
        logger.error(error_msg)
        raise Exception(error_msg)

    if config["retry_delay"] < 0:
        error_msg = "Retry delay must be non-negative"
        logger.error(error_msg)
        raise Exception(error_msg)

    # Check sync configuration (if still relevant)
    if config.get("sync_interval", 0) < 0:
        error_msg = "Sync interval must be non-negative"
        logger.error(error_msg)
        raise Exception(error_msg)

    if config.get("max_sync_age", 0) < 0:
        error_msg = "Max sync age must be non-negative"
        logger.error(error_msg)
        raise Exception(error_msg)

    # Check backup configuration (if still relevant)
    if config.get("backup_retention_days", 1) < 1:
        error_msg = "Backup retention days must be at least 1"
        logger.error(error_msg)
        raise ValueError(error_msg)  # Changed to ValueError

    return True


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    """Set up logging configuration.

    Args:
    ----
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file, if None logs to console only

    """
    log_config = {
        "level": log_level,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }

    if log_file and not IS_TEST_MODE:
        try:
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            log_config["filename"] = log_file
        except (OSError, PermissionError) as e:
            logger.warning(
                "Could not create log directory: %s. Logging to console only.", e
            )

    logging.basicConfig(**log_config)
    logger.info("Logging configured successfully")


def initialize_environment() -> bool:
    """Initialize database environment.

    Returns
    -------
        True if initialization successful, False otherwise

    """
    # Load environment variables
    load_dotenv()

    try:
        config = get_db_config()

        # Set up logging (adapt log file path if needed)
        log_dir = os.getenv("DEWEY_LOG_DIR", "/Users/srvo/dewey/logs")
        log_file = os.path.join(log_dir, "dewey_db.log")

        setup_logging(log_level="INFO", log_file=log_file)

        # Validate configuration
        validate_config()  # Raises exception on failure

        # Create necessary directories (skip in test mode)
        if not IS_TEST_MODE:
            try:
                dirs_to_create = [log_dir]
                # Add backup dir if still relevant
                # if config.get("backup_dir"):
                #    dirs_to_create.append(config["backup_dir"])

                for dir_path in dirs_to_create:
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                        logger.info("Created directory: %s", dir_path)
            except (OSError, PermissionError) as e:
                logger.warning(
                    "Could not create directories: %s. This is expected in test environments.", e
                )

        # Remove DuckDB specific environment settings
        # os.environ["DUCKDB_NO_VERIFY_CERTIFICATE"] = "1"
        # if config.get("motherduck_token"):
        #     os.environ["MOTHERDUCK_TOKEN"] = config["motherduck_token"]

        logger.info("Database environment initialized successfully for PostgreSQL")
        return True

    except (ValueError, Exception) as e:  # Catch validation errors too
        logger.error("Failed to initialize environment: %s", e)
        return False


def get_connection_string() -> str:
    """Get PostgreSQL database connection string.

    Returns
    -------
        Database connection string (DSN format)

    Raises
    ------
        ValueError: If required configuration parameters are missing.

    """
    config = get_db_config()

    # Validate required parameters exist before constructing string
    required_params = ["pg_host", "pg_port", "pg_user", "pg_dbname"]
    missing = [p for p in required_params if not config.get(p)]
    if missing:
        raise ValueError(
            "Missing required PostgreSQL config for connection string: %s" % missing)

    # Construct DSN (Data Source Name) string
    # Example: "postgresql://user:password@host:port/dbname"
    # Or use key=value format preferred by some libraries/pools:
    # "dbname=dewey_db user=myuser password=mypass host=localhost port=5432"

    # Using key=value format for psycopg2 pool compatibility
    dsn_parts = [
        f"dbname={config['pg_dbname']}",
        f"user={config['pg_user']}",
        f"host={config['pg_host']}",
        f"port={config['pg_port']}",
    ]
    # Only add password if it exists
    if config.get("pg_password"):
        dsn_parts.append(f"password={config['pg_password']}")

    return " ".join(dsn_parts)


# For testing purposes - enables test mode
def set_test_mode(enabled: bool = True) -> None:
    """Set test mode to skip file operations during tests.

    Args:
    ----
        enabled: Whether to enable test mode

    """
    global IS_TEST_MODE
    IS_TEST_MODE = enabled
