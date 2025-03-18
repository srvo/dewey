"""Database configuration module.

This module handles database configuration, initialization, and environment setup
for both local DuckDB and MotherDuck cloud databases.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database paths and configuration
LOCAL_DB_PATH = os.getenv('DEWEY_LOCAL_DB', '/Users/srvo/dewey/dewey.duckdb')
MOTHERDUCK_DB = os.getenv('DEWEY_MOTHERDUCK_DB', 'md:dewey@motherduck/dewey.duckdb')
MOTHERDUCK_TOKEN = os.getenv('MOTHERDUCK_TOKEN')

# Connection pool configuration
DEFAULT_POOL_SIZE = int(os.getenv('DEWEY_DB_POOL_SIZE', '5'))
MAX_RETRIES = int(os.getenv('DEWEY_DB_MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('DEWEY_DB_RETRY_DELAY', '1'))

# Sync configuration
SYNC_INTERVAL = int(os.getenv('DEWEY_SYNC_INTERVAL', '21600'))  # 6 hours in seconds
MAX_SYNC_AGE = int(os.getenv('DEWEY_MAX_SYNC_AGE', '604800'))  # 7 days in seconds

# Backup configuration
BACKUP_DIR = os.getenv('DEWEY_BACKUP_DIR', '/Users/srvo/dewey/backups')
BACKUP_RETENTION_DAYS = int(os.getenv('DEWEY_BACKUP_RETENTION_DAYS', '30'))

def get_db_config() -> Dict:
    """Get database configuration.
    
    Returns:
        Dictionary containing database configuration
    """
    return {
        'local_db_path': LOCAL_DB_PATH,
        'motherduck_db': MOTHERDUCK_DB,
        'motherduck_token': MOTHERDUCK_TOKEN,
        'pool_size': DEFAULT_POOL_SIZE,
        'max_retries': MAX_RETRIES,
        'retry_delay': RETRY_DELAY,
        'sync_interval': SYNC_INTERVAL,
        'max_sync_age': MAX_SYNC_AGE,
        'backup_dir': BACKUP_DIR,
        'backup_retention_days': BACKUP_RETENTION_DAYS
    }

def validate_config() -> bool:
    """Validate database configuration.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        # Check local database path
        local_db_dir = os.path.dirname(LOCAL_DB_PATH)
        if not os.path.exists(local_db_dir):
            os.makedirs(local_db_dir)
            logger.info(f"Created local database directory: {local_db_dir}")
            
        # Check backup directory
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
            logger.info(f"Created backup directory: {BACKUP_DIR}")
            
        # Check MotherDuck token
        if not MOTHERDUCK_TOKEN:
            logger.warning("MotherDuck token not found in environment")
            return False
            
        # Check pool configuration
        if DEFAULT_POOL_SIZE < 1:
            logger.error("Pool size must be at least 1")
            return False
            
        if MAX_RETRIES < 0:
            logger.error("Max retries must be non-negative")
            return False
            
        if RETRY_DELAY < 0:
            logger.error("Retry delay must be non-negative")
            return False
            
        # Check sync configuration
        if SYNC_INTERVAL < 0:
            logger.error("Sync interval must be non-negative")
            return False
            
        if MAX_SYNC_AGE < 0:
            logger.error("Max sync age must be non-negative")
            return False
            
        # Check backup configuration
        if BACKUP_RETENTION_DAYS < 1:
            logger.error("Backup retention days must be at least 1")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False

def setup_logging(log_level: str = 'INFO',
                 log_file: Optional[str] = None) -> None:
    """Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file, if None logs to console only
    """
    try:
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(console_handler)
        
        # Set up file handler if specified
        if log_file:
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
        logger.info("Logging configured successfully")
        
    except Exception as e:
        print(f"Failed to configure logging: {e}")

def initialize_environment() -> bool:
    """Initialize database environment.
    
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        # Set up logging
        log_file = os.path.join(
            os.path.dirname(LOCAL_DB_PATH),
            'logs/dewey_db.log'
        )
        setup_logging(log_level='INFO', log_file=log_file)
        
        # Validate configuration
        if not validate_config():
            logger.error("Invalid configuration")
            return False
            
        # Create necessary directories
        dirs_to_create = [
            os.path.dirname(LOCAL_DB_PATH),
            BACKUP_DIR,
            os.path.dirname(log_file)
        ]
        
        for dir_path in dirs_to_create:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.info(f"Created directory: {dir_path}")
                
        # Set up environment variables for DuckDB
        os.environ['DUCKDB_NO_VERIFY_CERTIFICATE'] = '1'
        os.environ['MOTHERDUCK_TOKEN'] = MOTHERDUCK_TOKEN
        
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
    return LOCAL_DB_PATH if local_only else MOTHERDUCK_DB 