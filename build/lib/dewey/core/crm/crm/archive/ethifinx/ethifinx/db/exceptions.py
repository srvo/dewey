class DatabaseError(Exception):
    """Base class for database-related errors."""

    pass


class DatabaseSaveError(DatabaseError):
    """Exception raised when saving to the database fails."""

    pass


class DatabaseRetrievalError(DatabaseError):
    """Exception raised when retrieving from the database fails."""

    pass
