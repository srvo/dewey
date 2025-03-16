# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025


class DatabaseError(Exception):
    """Base class for database-related errors."""


class DatabaseSaveError(DatabaseError):
    """Exception raised when saving to the database fails."""


class DatabaseRetrievalError(DatabaseError):
    """Exception raised when retrieving from the database fails."""
