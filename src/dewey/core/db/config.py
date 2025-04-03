"""Database configuration module.

This module handles database configuration, initialization, and environment setup
for both local DuckDB and MotherDuck cloud databases.
"""

import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables at import time to ensure variables are available
# but functions will reload them when called to ensure test mocks work
load_dotenv()

# Database paths and configuration
LOCAL_DB_PATH = os.getenv("DEWEY_LOCAL_DB", "/Users/srvo/dewey/dewey.duckdb")
MOTHERDUCK_DB = os.getenv("DEWEY_MOTHERDUCK_DB", "md:dewey@motherduck/dewey.duckdb")
MOTHERDUCK_TOKEN = os.getenv("MOTHERDUCK_TOKEN")

# Connection pool configuration
DEFAULT_POOL_SIZE = int(os.getenv("DEWEY_DB_POOL_SIZE", "5"))
MAX_RETRIES = int(os.getenv("DEWEY_DB_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("DEWEY_DB_RETRY_DELAY", "1"))

# Sync configuration
SYNC_INTERVAL = int(os.getenv("DEWEY_SYNC_INTERVAL", "21600"))  # 6 hours in seconds
MAX_SYNC_AGE = int(os.getenv("DEWEY_MAX_SYNC_AGE", "604800"))  # 7 days in seconds

# Backup configuration
BACKUP_DIR = os.getenv("DEWEY_BACKUP_DIR", "/Users/srvo/dewey/backups")
BACKUP_RETENTION_DAYS = int(os.getenv("DEWEY_BACKUP_RETENTION_DAYS", "30"))

# Flag to indicate if running in test mode
# This will be set by tests to skip directory creation
IS_TEST_MODE = False


def get_db_config() -> dict:
    """Get database configuration.

    Returns:
        Dictionary containing database configuration

    """
    # Read from environment each time to ensure we get the latest values
    # including any patched values in tests
    return {
        "local_db_path": os.getenv("DEWEY_LOCAL_DB", LOCAL_DB_PATH),
        "motherduck_db": os.getenv("DEWEY_MOTHERDUCK_DB", MOTHERDUCK_DB),
        "motherduck_token": os.getenv("MOTHERDUCK_TOKEN", MOTHERDUCK_TOKEN),
        "pool_size": int(os.getenv("DEWEY_DB_POOL_SIZE", str(DEFAULT_POOL_SIZE))),
        "max_retries": int(os.getenv("DEWEY_DB_MAX_RETRIES", str(MAX_RETRIES))),
        "retry_delay": int(os.getenv("DEWEY_DB_RETRY_DELAY", str(RETRY_DELAY))),
        "sync_interval": int(os.getenv("DEWEY_SYNC_INTERVAL", str(SYNC_INTERVAL))),
        "max_sync_age": int(os.getenv("DEWEY_MAX_SYNC_AGE", str(MAX_SYNC_AGE))),
        "backup_dir": os.getenv("DEWEY_BACKUP_DIR", BACKUP_DIR),
        "backup_retention_days": int(
            os.getenv("DEWEY_BACKUP_RETENTION_DAYS", str(BACKUP_RETENTION_DAYS))
        ),
    }


def validate_config() -> bool:
    """Validate database configuration.

    Returns:
        True if configuration is valid, False otherwise

    Raises:
        Exception: If the configuration is invalid

    """
    config = get_db_config()

    # Check for empty required values
    if not config["local_db_path"] or not config["motherduck_db"]:
        error_msg = "Local DB path and MotherDuck DB must be specified"
        logger.error(error_msg)
        raise Exception(error_msg)

    # Skip directory creation if in test mode
    if not IS_TEST_MODE:
        try:
            # Check local database path
            local_db_dir = os.path.dirname(config["local_db_path"])
            if not os.path.exists(local_db_dir):
                os.makedirs(local_db_dir)
                logger.info(f"Created local database directory: {local_db_dir}")

            # Check backup directory
            if not os.path.exists(config["backup_dir"]):
                os.makedirs(config["backup_dir"])
                logger.info(f"Created backup directory: {config['backup_dir']}")
        except (OSError, PermissionError) as e:
            logger.warning(
                f"Could not create directories: {e}. This is expected in test environments."
            )

    # Check MotherDuck token
    if not config["motherduck_token"]:
        error_msg = "MotherDuck token not found in environment"
        logger.error(error_msg)
        raise Exception(error_msg)

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

    # Check sync configuration
    if config["sync_interval"] < 0:
        error_msg = "Sync interval must be non-negative"
        logger.error(error_msg)
        raise Exception(error_msg)

    if config["max_sync_age"] < 0:
        error_msg = "Max sync age must be non-negative"
        logger.error(error_msg)
        raise Exception(error_msg)

    # Check backup configuration
    if config["backup_retention_days"] < 1:
        error_msg = "Backup retention days must be at least 1"
        logger.error(error_msg)
        raise Exception(error_msg)

    return True


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    """Set up logging configuration.

    Args:
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
                f"Could not create log directory: {e}. Logging to console only."
            )

    logging.basicConfig(**log_config)
    logger.info("Logging configured successfully")


def initialize_environment() -> bool:
    """Initialize database environment.

    Returns:
        True if initialization successful, False otherwise

    """
    # Load environment variables
    load_dotenv()

    try:
        config = get_db_config()

        # Set up logging
        log_file = os.path.join(
            os.path.dirname(config["local_db_path"]), "logs/dewey_db.log"
        )
        setup_logging(log_level="INFO", log_file=log_file)

        # Validate configuration
        if not validate_config():
            logger.error("Invalid configuration")
            return False

        # Create necessary directories (skip in test mode)
        if not IS_TEST_MODE:
            try:
                dirs_to_create = [
                    os.path.dirname(config["local_db_path"]),
                    config["backup_dir"],
                    os.path.dirname(log_file),
                ]

                for dir_path in dirs_to_create:
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                        logger.info(f"Created directory: {dir_path}")
            except (OSError, PermissionError) as e:
                logger.warning(
                    f"Could not create directories: {e}. This is expected in test environments."
                )

        # Set up environment variables for DuckDB
        os.environ["DUCKDB_NO_VERIFY_CERTIFICATE"] = "1"
        os.environ["MOTHERDUCK_TOKEN"] = config["motherduck_token"]

        logger.info("Database environment initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize environment: {e}")
        return False


def get_connection_string(local_only: bool = False) -> str:
    """Get database connection string.

    Args:
        local_only: Whether to return local database path only

    Returns:
        Database connection string

    """
    config = get_db_config()

    if local_only:
        return config["local_db_path"]
    else:
        # Add token to MotherDuck connection string if available
        if config["motherduck_token"]:
            return f"{config['motherduck_db']}?motherduck_token={config['motherduck_token']}"
        return config["motherduck_db"]


# For testing purposes - enables test mode
def set_test_mode(enabled: bool = True) -> None:
    """Set test mode to skip file operations during tests.

    Args:
        enabled: Whether to enable test mode

    """
    global IS_TEST_MODE
    IS_TEST_MODE = enabled
