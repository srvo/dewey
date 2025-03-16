"""Database package for email processing system.

This package provides:
- Database models and schema definitions
- Connection management and pooling
- Transaction handling
- Database initialization and migrations
"""

from .db_connector import DatabaseConnection, db


def get_models():
    """Lazy import models to avoid AppRegistryNotReady errors."""
    from .models import (
        Contact,
        Email,
        EmailContactAssociation,
        EmailLabelHistory,
        MessageThreadAssociation,
        RawEmail,
    )

    return {
        "Contact": Contact,
        "Email": Email,
        "EmailContactAssociation": EmailContactAssociation,
        "EmailLabelHistory": EmailLabelHistory,
        "MessageThreadAssociation": MessageThreadAssociation,
        "RawEmail": RawEmail,
    }


__all__ = [
    "DatabaseConnection",
    "db",
    "get_models",
]

default_app_config = "database.apps.DatabaseConfig"
