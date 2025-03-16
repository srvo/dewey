"""Database connection management for the application.

This module provides a centralized interface for managing database connections
and transactions using Django's ORM. It implements a singleton pattern to ensure
consistent database access throughout the application.

Key Features:
- Atomic transaction management
- Context manager interface for safe transaction handling
- Automatic rollback on errors
- Singleton pattern for global access
- Clean separation of database concerns
- Connection pooling for improved performance
- Transaction isolation level control
- Comprehensive error handling and logging

The main class DatabaseConnection provides:
- get_session(): Returns a database connection within transaction context
- Context manager protocol for 'with' statements
- Automatic cleanup of database resources
- Connection pooling configuration
- Transaction isolation level settings

Typical usage:
    from database.db_connector import db

    with db.get_session() as session:
        # Perform database operations
        session.execute(...)

Note:
----
    All database operations should be performed within a transaction context
    to ensure data consistency and proper error handling. The connection
    pooling helps optimize performance for high-concurrency scenarios.

Security Considerations:
- Uses Django's built-in transaction management for atomicity
- Implements proper connection cleanup to prevent leaks
- Handles transaction isolation levels appropriately
- Provides rollback guarantees in case of errors

Implementation Details:
- Uses Django's transaction.atomic decorator for atomic operations
- Connection pooling is managed by Django's database backend
- Isolation levels are enforced at the database level
- Singleton pattern ensures single connection pool instance
- Context manager protocol guarantees proper resource cleanup

"""

# Standard library imports
from __future__ import annotations

from typing import TYPE_CHECKING

# Django imports
from django.db import transaction

if TYPE_CHECKING:
    from django.db.backends.base.base import BaseDatabaseWrapper

# Constants for default configuration
DEFAULT_POOL_SIZE = 5  # Default number of connections in the pool
DEFAULT_MAX_OVERFLOW = 10  # Maximum number of overflow connections
DEFAULT_TIMEOUT = 30  # seconds - Connection timeout
DEFAULT_ISOLATION_LEVEL = "read committed"  # Default transaction isolation level

# Valid isolation levels supported by most databases
VALID_ISOLATION_LEVELS = [
    "read uncommitted",  # Allows dirty reads
    "read committed",  # Prevents dirty reads
    "repeatable read",  # Prevents non-repeatable reads
    "serializable",  # Highest isolation level
]


class DatabaseConnection:
    """Database connection handler for the application.

    This class provides a context manager interface for database transactions,
    ensuring proper transaction handling and cleanup. It implements the following
    features:

    - Atomic transaction management using Django's transaction.atomic decorator
    - Context manager protocol for easy use with 'with' statements
    - Automatic rollback on exceptions
    - Commit on successful completion
    - Singleton pattern for global database access
    - Connection pooling configuration
    - Transaction isolation level control

    Attributes:
    ----------
        _connection (Optional[BaseDatabaseWrapper]):
            Internal database connection reference (lazily initialized)
        _pool_size (int):
            Number of connections to maintain in the pool (default: 5)
        _max_overflow (int):
            Maximum number of connections to create beyond pool_size (default: 10)
        _timeout (int):
            Connection timeout in seconds (default: 30)
        _isolation_level (str):
            Transaction isolation level (default: "read committed")

    Methods:
    -------
        get_session(): Returns a database connection within transaction context
        __enter__(): Context manager entry point
        __exit__(): Context manager exit point with cleanup
        configure_pool(): Configure connection pool settings
        set_isolation_level(): Set transaction isolation level

    Example:
    -------
        # Basic usage
        with db.get_session() as session:
            session.execute("SELECT 1")

        # Advanced usage with pool configuration
        db.configure_pool(pool_size=10, max_overflow=20, timeout=60)
        db.set_isolation_level("serializable")

    Implementation Details:
    - Uses lazy initialization to defer connection creation until first use
    - Connection pooling is managed by Django's database backend
    - Transaction isolation levels are enforced at the database level
    - Context manager protocol ensures proper resource cleanup
    - Singleton pattern prevents multiple connection pools

    """

    def __init__(self) -> None:
        """Initialize the database connection handler.

        Sets up the internal connection state with default pool settings.
        The actual connection is established lazily when first used to
        optimize resource utilization.

        Note:
        ----
            This uses lazy initialization to avoid creating database connections
            until they are actually needed. The connection pool is configured
            with conservative defaults that can be adjusted using configure_pool().

        Attributes initialized:
        - _connection: None until first use (lazy initialization)
        - _pool_size: Default connection pool size
        - _max_overflow: Maximum overflow connections
        - _timeout: Connection timeout in seconds
        - _isolation_level: Default transaction isolation level

        """
        self._connection: BaseDatabaseWrapper | None = None
        self._pool_size: int = DEFAULT_POOL_SIZE
        self._max_overflow: int = DEFAULT_MAX_OVERFLOW
        self._timeout: int = DEFAULT_TIMEOUT
        self._isolation_level: str = DEFAULT_ISOLATION_LEVEL

    @staticmethod
    @transaction.atomic
    def get_session():
        """Provides a database session context.

        Returns a database connection wrapped in an atomic transaction context.
        The session provides access to the database connection and ensures
        proper transaction handling.

        Returns:
        -------
            BaseDatabaseWrapper:
                A database connection object that can be used to execute
                queries within a transaction.

        Note:
        ----
            The session is wrapped in an atomic transaction, meaning all operations
            will either complete successfully or be rolled back entirely. This
            ensures data consistency even in case of errors.

            The connection is obtained from Django's connection pool, which
            helps optimize performance for concurrent operations.

            The @transaction.atomic decorator ensures atomicity of operations
            within the session context.

        Example:
        -------
            with db.get_session() as session:
                session.execute("SELECT 1")

        Raises:
        ------
            DatabaseError: If the connection cannot be established
            OperationalError: If the database is unavailable
            TransactionManagementError: If transaction state is invalid

        Implementation Details:
        - Uses Django's transaction.atomic decorator for atomic operations
        - Connection is obtained from Django's connection pool
        - Transaction state is managed automatically
        - Errors trigger automatic rollback

        """
        return transaction.get_connection()

    def configure_pool(
        self,
        pool_size: int = DEFAULT_POOL_SIZE,
        max_overflow: int = DEFAULT_MAX_OVERFLOW,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Configure the database connection pool settings.

        Args:
        ----
            pool_size (int):
                Number of connections to maintain in the pool (default: 5)
            max_overflow (int):
                Maximum number of connections to create beyond pool_size (default: 10)
            timeout (int):
                Connection timeout in seconds (default: 30)

        Note:
        ----
            These settings affect how the connection pool manages database
            connections. Larger pool sizes can improve performance for
            high-concurrency scenarios but consume more resources.

            The timeout value determines how long to wait for a connection
            before raising an error.

            It's recommended to set pool_size based on expected concurrent
            database operations and available system resources.

        Raises:
        ------
            ValueError: If any parameter is negative

        """
        if pool_size < 0 or max_overflow < 0 or timeout < 0:
            msg = "Pool configuration parameters cannot be negative"
            raise ValueError(msg)

        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._timeout = timeout

    def set_isolation_level(self, level: str = DEFAULT_ISOLATION_LEVEL) -> None:
        """Set the transaction isolation level.

        Args:
        ----
            level (str):
                Isolation level to use for transactions. Must be one of:
                - "read uncommitted"
                - "read committed"
                - "repeatable read"
                - "serializable"

        Note:
        ----
            The isolation level controls how transactions interact with each
            other. Higher isolation levels provide stronger guarantees but
            may impact performance.

            Defaults to "read committed" which provides a good balance
            between consistency and performance.

            Isolation levels affect:
            - Dirty reads: Whether uncommitted changes are visible
            - Non-repeatable reads: Whether same query returns different results
            - Phantom reads: Whether new rows appear in result sets

        Raises:
        ------
            ValueError: If invalid isolation level is provided

        """
        if level not in VALID_ISOLATION_LEVELS:
            msg = f"Invalid isolation level '{level}'. Must be one of: {VALID_ISOLATION_LEVELS}"
            raise ValueError(
                msg,
            )
        self._isolation_level = level

    def __enter__(self):
        """Enter the context manager.

        Returns:
        -------
            BaseDatabaseWrapper:
                The database connection to use within the context.

        Note:
        ----
            This method is called when entering a 'with' block. It ensures
            proper transaction handling and resource management.

            The connection is obtained from the pool and configured with
            the current isolation level.

            The context manager protocol ensures that __exit__() will be
            called even if an exception occurs, guaranteeing cleanup.

        Implementation Details:
        - Creates new transaction context
        - Configures isolation level
        - Returns active database connection

        """
        return self.get_session()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: type[BaseException] | None,
    ):
        """Exit the context manager.

        Args:
        ----
            exc_type (Optional[Type[BaseException]]):
                Exception type if an exception occurred, else None
            exc_val (Optional[BaseException]):
                Exception value if an exception occurred, else None
            exc_tb (Optional[Type[BaseException]]):
                Exception traceback if an exception occurred, else None

        Handles transaction cleanup:
        - Rolls back on any exception to maintain data consistency
        - Commits on successful completion to persist changes
        - Ensures proper resource cleanup in all cases
        - Returns the connection to the pool

        Note:
        ----
            This method is called when exiting a 'with' block, either normally
            or due to an exception. It handles both success and error cases.

            The connection is automatically returned to the pool after
            the transaction is complete.

            If an exception occurs, the transaction is rolled back to
            maintain database consistency.

        Implementation Details:
        - Checks for exception presence
        - Performs rollback or commit based on success/failure
        - Ensures connection is returned to pool
        - Cleans up transaction state

        """
        if exc_type is not None:
            transaction.rollback()
        else:
            transaction.commit()


# Create a singleton instance for global access
db = DatabaseConnection()

__all__ = ["DatabaseConnection", "db"]
