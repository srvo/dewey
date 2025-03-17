"""
Database and Data Storage Module
==============================

This module provides unified database and data storage functionality for the EthiFinX platform.
It combines local database operations with cloud storage capabilities.

Components:
----------
- Database: Local DuckDB instance for efficient data storage and querying
- Data Store: Interface for database operations and S3 backup functionality
- Migrations: Database schema version control
"""

from ethifinx.db.models import (
    CompanyContext,
    Exclusion,
    Portfolio,
    Research,
    ResearchResults,
    ResearchSources,
    TickHistory,
    Universe,
)

from .data_store import DataStore, get_connection

__all__ = [
    "Universe",
    "CompanyContext",
    "Research",
    "ResearchResults",
    "ResearchSources",
    "Portfolio",
    "Exclusion",
    "TickHistory",
    "DataStore",
    "get_connection",
]
