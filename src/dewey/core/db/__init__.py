"""Database module for the Dewey project.

This module provides database connection and utility functions.
"""

from .database import get_duckdb_connection, ensure_table_exists
from .db_utils import initialize_crm_database, store_email, store_contact, check_database_schema
from .models import (
    TABLE_SCHEMAS,
    TABLE_INDEXES,
    EMAIL_ANALYSES_SCHEMA,
    CONTACTS_SCHEMA,
    EMAIL_LABELS_SCHEMA
)

__all__ = [
    'get_duckdb_connection',
    'ensure_table_exists',
    'initialize_crm_database',
    'store_email',
    'store_contact',
    'check_database_schema',
    'TABLE_SCHEMAS',
    'TABLE_INDEXES',
    'EMAIL_ANALYSES_SCHEMA',
    'CONTACTS_SCHEMA',
    'EMAIL_LABELS_SCHEMA'
] 