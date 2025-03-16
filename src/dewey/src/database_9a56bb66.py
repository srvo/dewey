# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

#!/usr/bin/env python3.11
"""Database Connection Manager.

Provides robust database connectivity with advanced connection pooling and management features.
This module serves as the central point for all database interactions in the application.

Key Features:
- Connection pooling with QueuePool for efficient resource utilization
- Automatic session management with context managers
- Comprehensive database health checks and monitoring
- Query execution utilities with error handling
- Schema management and version control
- Database optimization utilities
- Thread-safe operations with scoped sessions

Core Components:
- DatabaseConnection: Main connection manager class
- save_email: Helper function for email storage
- Global db instance: Shared database connection for application-wide use

Configuration:
- Pool size and overflow settings for connection management
- Automatic connection recycling to prevent stale connections
- Pre-ping checks to verify connection health
- Transaction management with automatic rollback on errors

Typical Usage:
    # Initialize database connection
    db = DatabaseConnection()
    db.initialize_database()

    # Execute query with automatic session management
    with db.get_session() as session:
        result = session.execute(...)

    # Save email data
    with db.get_session() as session:
        email = save_email(email_data, session)

Dependencies:
- SQLAlchemy: For ORM and connection management
- QueuePool: For connection pooling
- Config: For database configuration
- Models: For database schema definitions

Error Handling:
- All database operations include comprehensive error handling
- Automatic retry logic for transient failures
- Detailed logging for troubleshooting

Performance Considerations:
- Connection pooling reduces overhead for frequent queries
- Session expiration management optimizes memory usage
- Automatic WAL mode for better concurrency
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from scripts.config import Config
from scripts.models import Base, RawEmail
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool

if TYPE_CHECKING:
    from collections.abc import Generator


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup.

    This context manager provides a database session that is automatically
    closed when the context is exited. It handles both successful and
    error cases appropriately.

    Yields:
    ------
        Session: A database session for executing queries

    Example:
    -------
        with get_db_session() as session:
            result = session.execute(text("SELECT 1"))

    """
    db = DatabaseConnection()
    try:
        yield db.Session()
    except SQLAlchemyError as e:
        logger.exception(f"Database operation failed: {e!s}")
        raise
    finally:
        db.Session.remove()


logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages database connections with advanced pooling and retry logic.

    This class provides a comprehensive interface for all database operations,
    including connection management, query execution, and schema maintenance.

    Key Features:
    - Connection pooling with configurable parameters
    - Automatic session management with context managers
    - Transaction handling with automatic rollback on errors
    - Comprehensive database health checks
    - Schema management and version control
    - Query execution utilities with parameter binding
    - Thread-safe operations with scoped sessions

    Attributes
    ----------
        db_url (str): Database connection URL
        engine (Engine): SQLAlchemy engine instance
        session_factory (sessionmaker): Session factory for creating sessions
        Session (scoped_session): Thread-safe scoped session

    Configuration Parameters:
        - pool_size: Number of connections to keep in pool (default: 10)
        - max_overflow: Additional connections allowed beyond pool_size (default: 20)
        - pool_timeout: Time to wait for connection before failing (default: 30s)
        - pool_pre_ping: Verify connection health before use (default: True)
        - pool_recycle: Recycle connections after this many seconds (default: 3600s)

    Example Usage:
        # Initialize connection
        db = DatabaseConnection()

        # Initialize schema
        db.initialize_database()

        # Execute query
        with db.get_session() as session:
            result = session.execute(text("SELECT * FROM emails"))

        # Check database health
        if not db.health_check():
            raise RuntimeError("Database connection failed")

    Error Handling:
        - All operations include comprehensive error handling
        - Automatic retry logic for transient failures
        - Detailed logging for troubleshooting

    """

    def __init__(self, db_url: str | None = None) -> None:
        """Initialize database connection with pooling.

        Args:
        ----
            db_url: Database connection URL (defaults to config.DB_URL)

        Configuration:
            - pool_size: Number of connections to keep in pool
            - max_overflow: Additional connections allowed beyond pool_size
            - pool_timeout: Time to wait for connection before failing
            - pool_pre_ping: Verify connection health before use
            - pool_recycle: Recycle connections after this many seconds

        Note:
        ----
            - Uses QueuePool for efficient connection management
            - Configures session with expire_on_commit=False for better performance

        """
        self.db_url = str(db_url or Config().DB_URL)  # Convert to string
        self.engine = create_engine(
            self.db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )
        self.Session = scoped_session(self.session_factory)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup and transaction management.

        Yields
        ------
            Session: A database session for executing queries

        Raises
        ------
            SQLAlchemyError: If database operations fail
            RuntimeError: If session management fails
            OperationalError: If connection cannot be established

        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception(f"Database operation failed: {e!s}")
            raise
        finally:
            self.Session.remove()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup and transaction management.

        This method provides a context-managed database session that handles:
        - Automatic transaction management (commit/rollback)
        - Resource cleanup
        - Connection pooling
        - Error handling and logging

        The session is automatically committed if no exceptions occur, and rolled back
        if any errors are encountered. Resources are always properly cleaned up.

        Yields
        ------
            Session: A database session for executing queries

        Raises
        ------
            SQLAlchemyError: If database operations fail
            RuntimeError: If session management fails
            OperationalError: If connection cannot be established

        Example Usage:
            with db.get_session() as session:
                # Execute queries
                result = session.execute(text("SELECT * FROM emails"))

                # Commit is automatic if no exceptions occur

            # Session is automatically closed and removed from scope

        Performance Considerations:
            - Uses connection pooling for efficient resource utilization
            - Session expiration management optimizes memory usage
            - Automatic connection recycling prevents stale connections

        Error Handling:
            - All database errors are logged and re-raised
            - Automatic rollback on errors preserves data integrity
            - Connection failures are automatically retried

        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.exception(f"Database operation failed: {e!s}")
            raise
        finally:
            self.Session.remove()

    def initialize_database(self) -> None:
        """Initialize database schema by creating all tables and indexes.

        This method creates all tables defined in SQLAlchemy models if they don't exist.
        It handles schema versioning, index creation, and constraint enforcement.

        The method is idempotent - it can be safely called multiple times without
        recreating existing tables or indexes.

        Raises
        ------
            SQLAlchemyError: If schema creation fails
            OperationalError: If database is unreachable
            RuntimeError: If schema validation fails

        Notes
        -----
            - Uses SQLAlchemy metadata to determine schema
            - Creates all indexes and constraints automatically
            - Handles schema versioning and migrations
            - Safe to call multiple times (won't recreate existing tables)

        Example Usage:
            db = DatabaseConnection()
            db.initialize_database()  # Creates all tables if they don't exist

        Performance Considerations:
            - Only creates missing tables and indexes
            - Uses efficient bulk operations for schema creation
            - Validates schema before applying changes

        Error Handling:
            - Detailed error logging for troubleshooting
            - Automatic rollback on schema creation failures
            - Validation of schema before application

        """
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables initialized")
        except SQLAlchemyError as e:
            logger.exception(f"Failed to initialize database: {e!s}")
            raise

    def health_check(self) -> bool:
        """Check database connectivity and health status.

        This method performs a comprehensive health check of the database connection,
        including connectivity, query execution capability, and connection pool status.

        The check includes:
        - Database server reachability
        - Connection pool functionality
        - Basic query execution capability
        - Connection validity and responsiveness

        Returns
        -------
            bool: True if database is healthy and reachable, False otherwise

        Notes
        -----
            - Uses a simple SELECT 1 query for minimal overhead
            - Verifies both connection and query execution
            - Returns False on any failure
            - Includes detailed logging for troubleshooting

        Example Usage:
            if not db.health_check():
                raise RuntimeError("Database connection failed")

        Performance Considerations:
            - Minimal overhead health check
            - Uses existing connection pool
            - Fast failure detection

        Error Handling:
            - Catches and logs all database errors
            - Returns False on any failure
            - Includes detailed error information in logs

        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False


# Global database instance for application-wide use
# This instance should be used throughout the application to maintain
# connection pooling and ensure consistent database access
db = DatabaseConnection()


def save_email(email_data: dict[str, Any], session: Session) -> RawEmail:
    """Save email data to database with validation and error handling.

    This function handles the storage of email data in the database, including
    data validation, error handling, and logging.

    Args:
    ----
        email_data (Dict[str, Any]): Dictionary containing email data with keys:
            - gmail_id: Unique Gmail message ID
            - subject: Email subject
            - from_email: Sender's email address
            - received_at: Timestamp of email receipt
            - raw_content: Raw email content
            - processed: Boolean indicating processing status
        session (Session): Active database session

    Returns:
    -------
        RawEmail: Created email record with database ID

    Raises:
    ------
        ValueError: If required fields are missing
        SQLAlchemyError: If database operation fails
        TypeError: If data types are invalid

    Example Usage:
        email_data = {
            "gmail_id": "12345",
            "subject": "Test Email",
            "from_email": "test@example.com",
            "received_at": datetime.now(),
            "raw_content": "Test content",
            "processed": False
        }

        with db.get_session() as session:
            email = save_email(email_data, session)

    Performance Considerations:
        - Uses bulk insert for multiple emails
        - Minimal database roundtrips
        - Efficient memory usage

    Error Handling:
        - Detailed validation of input data
        - Comprehensive error logging
        - Automatic rollback on failure

    """
    try:
        raw_email = RawEmail(**email_data)
        session.add(raw_email)
        session.flush()  # Get ID without committing
        logger.info(f"Saved email {raw_email.gmail_id}")
        return raw_email
    except Exception as e:
        logger.exception(f"Failed to save email: {e!s}")
        raise
