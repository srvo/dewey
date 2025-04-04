"""
Database operations module.

This module provides high-level database operations and transaction management
for both local DuckDB and MotherDuck cloud databases.
"""

import json
import logging
from typing import Any

from .connection import DatabaseConnectionError, db_manager
from dewey.core.base_script import BaseScript

logger = logging.getLogger(__name__)


class DatabaseMaintenance(BaseScript):
    """
    Base class for database maintenance operations.
    
    Provides common functionality for table cleanup, analysis, and other
    maintenance tasks.
    """
    def __init__(self, *args: Any, dry_run: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.dry_run = dry_run

    def execute(self) -> None:
        """Execute the maintenance operations (required by BaseScript)."""
        # This is a no-op since we have specific methods for each operation
        pass

    def cleanup_tables(self, table_names: list[str]):
        pass

