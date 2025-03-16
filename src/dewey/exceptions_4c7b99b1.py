from __future__ import annotations


class LedgerError(Exception):
    """Base class for all ledger-related errors."""

    def __init__(self, message: str, tx_hash: str | None = None) -> None:
        self.tx_hash = tx_hash
        self.message = message
        super().__init__(message)


class ClassificationError(LedgerError):
    """Failed to categorize transaction."""

    def __init__(self, message: str, description: str, tx_hash: str) -> None:
        super().__init__(f"{message}: '{description[:50]}'", tx_hash)
        self.description = description


class APIConnectionError(LedgerError):
    """Failed to connect to external API."""


class FileIntegrityError(LedgerError):
    """Invalid file format or corrupted data."""


class ValidationError(LedgerError):
    """Data validation failed."""
