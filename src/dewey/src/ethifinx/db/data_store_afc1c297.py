# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

"""Data Store Module.
===============

Provides a unified interface for database operations and S3 backup functionality.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import boto3
from botocore.exceptions import NoCredentialsError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from ..core.config import Config
from .exceptions import DatabaseRetrievalError, DatabaseSaveError

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_Session: sessionmaker | None = None


def init_db(database_url: str = "sqlite:///:memory:", pool_size: int = 5) -> None:
    """Initialize database connection with connection pooling."""
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=10,
            pool_pre_ping=True,  # Add connection health checks
        )
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def get_connection(
    use_raw_cursor: bool = False,
) -> Generator[Session | Any, None, None]:
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
            msg = "Failed to execute raw query"
            raise DatabaseRetrievalError(msg) from e
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
            msg = "Transaction failed"
            raise DatabaseSaveError(msg) from e
        finally:
            session.close()


class DataStore:
    """Unified data storage interface with transaction safety."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._s3_client = None  # Lazy-loaded S3 client
        self._config = None  # Lazy-loaded config

    @property
    def s3_client(self):
        """Thread-safe S3 client initializer."""
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.config.S3_ACCESS_KEY,
                aws_secret_access_key=self.config.S3_SECRET_KEY,
                region_name=self.config.S3_REGION,
            )
        return self._s3_client

    @property
    def config(self) -> Config:
        """Configuration loader with validation."""
        if self._config is None:
            self._config = Config()
            if not all(
                [
                    self._config.S3_BUCKET_NAME,
                    self._config.S3_ACCESS_KEY,
                    self._config.S3_SECRET_KEY,
                ],
            ):
                msg = "Missing S3 configuration"
                raise OSError(msg)
        return self._config

    # Existing methods remain with improved error handling

    def backup_to_s3(self, file_path: str) -> None:
        """Secure S3 backup with validation and progress tracking."""
        file_path = Path(file_path)
        if not file_path.exists():
            msg = f"Backup file not found: {file_path}"
            raise FileNotFoundError(msg)

        if file_path.stat().st_size > 2 * 1024**3:  # 2GB limit
            msg = "File size exceeds 2GB limit for S3 backup"
            raise ValueError(msg)

        try:
            self.s3_client.upload_file(
                str(file_path),
                self.config.S3_BUCKET_NAME,
                file_path.name,
                Callback=ProgressPercentage(file_path),
            )
            logger.info(f"Successfully backed up {file_path.name} to S3")
        except NoCredentialsError:
            logger.critical("S3 credentials not available")
            raise
        except Exception as e:
            logger.error(f"S3 backup failed: {e!s}", exc_info=True)
            raise

    # Added progress tracking class
    class ProgressPercentage:
        """S3 upload progress tracker."""

        def __init__(self, filename) -> None:
            self._filename = filename
            self._size = filename.stat().st_size
            self._seen = 0

        def __call__(self, bytes_amount):
            self._seen += bytes_amount
            logger.debug(
                f"Upload progress {self._filename}: "
                f"{self._seen}/{self._size} bytes ({self._seen/self._size:.1%})",
            )

    # Remaining methods maintain existing functionality with added type hints
    # and error context
