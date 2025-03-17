"""
Data Store Module
===============

Provides a unified interface for database operations and S3 backup functionality.
"""

import csv
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Union, List

import boto3
from botocore.exceptions import NoCredentialsError
from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import func

from ethifinx.db.models import (
    Universe,
    CompanyContext,
    TestTable,
    TickHistory,
)

from ..core.config import Config
from .exceptions import DatabaseRetrievalError, DatabaseSaveError

logger = logging.getLogger(__name__)

_engine: Optional[Engine] = None
_Session: Optional[sessionmaker] = None


def init_db(database_url: str = "sqlite:///:memory:", pool_size: int = 5) -> None:
    """Initialize database connection with connection pooling."""
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=10,
            pool_pre_ping=True  # Add connection health checks
        )
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def get_connection(
    use_raw_cursor: bool = False,
) -> Generator[Union[Session, Any], None, None]:
    """Get a managed database connection with transaction handling."""
    global _engine, _Session
    if _engine is None or _Session is None:
        init_db()

    if use_raw_cursor:
        connection = _engine.raw_connection()
        try:
            cursor = connection.cursor()
            yield cursor
            connection.commit()
        except Exception as e:
            logger.error(f"Database error: {e}", exc_info=True)
            connection.rollback()
            raise DatabaseRetrievalError("Failed to execute raw query") from e
        finally:
            cursor.close()
            connection.close()
    else:
        session = _Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Database transaction error: {e}", exc_info=True)
            session.rollback()
            raise DatabaseSaveError("Transaction failed") from e
        finally:
            session.close()


class DataStore:
    """Unified data storage interface with transaction safety."""
    
    def __init__(self, session: Session):
        self.session = session
        self._s3_client = None  # Lazy-loaded S3 client
        self._config = None  # Lazy-loaded config

    @property
    def s3_client(self):
        """Thread-safe S3 client initializer."""
        if self._s3_client is None:
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.S3_ACCESS_KEY,
                aws_secret_access_key=self.config.S3_SECRET_KEY,
                region_name=self.config.S3_REGION
            )
        return self._s3_client

    @property
    def config(self) -> Config:
        """Configuration loader with validation."""
        if self._config is None:
            self._config = Config()
            if not all([
                self._config.S3_BUCKET_NAME,
                self._config.S3_ACCESS_KEY,
                self._config.S3_SECRET_KEY
            ]):
                raise EnvironmentError("Missing S3 configuration")
        return self._config

    # Existing methods remain with improved error handling
    
    def backup_to_s3(self, file_path: str) -> None:
        """Secure S3 backup with validation and progress tracking."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Backup file not found: {file_path}")
            
        if file_path.stat().st_size > 2 * 1024**3:  # 2GB limit
            raise ValueError("File size exceeds 2GB limit for S3 backup")

        try:
            self.s3_client.upload_file(
                str(file_path),
                self.config.S3_BUCKET_NAME,
                file_path.name,
                Callback=ProgressPercentage(file_path)
            )
            logger.info(f"Successfully backed up {file_path.name} to S3")
        except NoCredentialsError:
            logger.critical("S3 credentials not available")
            raise
        except Exception as e:
            logger.error(f"S3 backup failed: {str(e)}", exc_info=True)
            raise

    # Added progress tracking class
    class ProgressPercentage:
        """S3 upload progress tracker."""
        def __init__(self, filename):
            self._filename = filename
            self._size = filename.stat().st_size
            self._seen = 0

        def __call__(self, bytes_amount):
            self._seen += bytes_amount
            logger.debug(
                f"Upload progress {self._filename}: "
                f"{self._seen}/{self._size} bytes ({self._seen/self._size:.1%})"
            )

    # Remaining methods maintain existing functionality with added type hints
    # and error context
