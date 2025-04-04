"""Database migration manager for Dewey (PostgreSQL).

This module provides tools for managing database migrations, including:
- Tracking applied migrations
- Running migrations in order
- Handling rollbacks
"""

import importlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Tuple, Optional

import yaml

from dewey.core.base_script import BaseScript
from dewey.utils.database import (
    execute_query,
    fetch_all,
    fetch_one,
    insert_row,
    get_db_cursor,
    initialize_pool,
    close_pool,
    table_exists,
)


class MigrationManager(BaseScript):
    """Manages database migrations for Dewey.

    This class handles tracking, applying, and rolling back database migrations.
    It ensures migrations are applied in the correct order and only once.
    """

    MIGRATIONS_TABLE = "migrations"

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        """Initialize the migration manager.

        Args:
        ----
            config: Configuration dictionary
            **kwargs: Additional keyword arguments

        """
        super().__init__(config=config, **kwargs)
        self.migrations_dir = Path(
            self.get_config_value(
                "migrations_directory",
                default=str(Path(__file__).parent / "migration_files"),
            ),
        )
        # self.conn = None # Connection managed by pool now

    def run(self) -> None:
        """Run the migration manager to apply pending migrations."""
        try:
            initialize_pool()  # Ensure pool is ready
            self._ensure_migrations_table()
            pending_migrations = self._get_pending_migrations()

            if not pending_migrations:
                self.logger.info("No pending migrations to apply.")
                return

            self.logger.info(f"Found {len(pending_migrations)} pending migrations.")
            for migration_file, migration_module in pending_migrations:
                self._apply_migration(migration_file, migration_module)

            self.logger.info("All migrations applied successfully.")

        except Exception as e:
            self.logger.exception(f"Error during migration: {e}")
            raise
        finally:
            close_pool()  # Close pool when done
            # No manual connection closing needed
            # if self.conn:
            #     self.conn.close()
            #     self.conn = None

    def execute(self) -> None:
        """Execute the migration manager to apply pending migrations."""
        # If BaseScript requires execute, just call run.
        self.run()

    def _ensure_migrations_table(self) -> None:
        """Ensure the migrations tracking table exists using utility functions."""
        # Check if table exists using the utility
        if not table_exists(self.MIGRATIONS_TABLE):
            self.logger.info(f"Migrations table '{self.MIGRATIONS_TABLE}' not found. Creating...")
            # Use standard SQL types compatible with PostgreSQL
            columns_definition = (
                "id SERIAL PRIMARY KEY, "
                "migration_name VARCHAR(255) NOT NULL UNIQUE, "  # Added UNIQUE constraint
                "applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, "  # Use TIMESTAMPTZ
                "success BOOLEAN NOT NULL, "
                "details TEXT"
            )
            # Use execute_query for DDL
            create_table_query = f"CREATE TABLE {self.MIGRATIONS_TABLE} ({columns_definition})"
            try:
                execute_query(create_table_query)
                self.logger.info(f"Successfully created migrations table '{self.MIGRATIONS_TABLE}'.")
            except Exception as e:
                self.logger.error(f"Failed to create migrations table: {e}")
                raise
        else:
            self.logger.debug(f"Migrations table '{self.MIGRATIONS_TABLE}' already exists.")

    def _get_applied_migrations(self) -> list[str]:
        """Get a list of already applied migrations using utility functions."""
        # Query uses %s placeholders implicitly handled by fetch_all
        query = f"""
        SELECT migration_name FROM {self.MIGRATIONS_TABLE}
        WHERE success = TRUE
        ORDER BY applied_at
        """
        try:
            results = fetch_all(query)
            return [row[0] for row in results]
        except Exception as e:
            # Log error and return empty list or re-raise depending on desired behavior
            self.logger.error(f"Error fetching applied migrations: {e}")
            # Depending on requirements, you might want to raise e here
            return []

    def _get_available_migrations(self) -> list[str]:
        """Get a list of available migration files.

        Returns
        -------
            List of available migration filenames

        """
        migration_files = []

        # Ensure the migrations directory exists
        if not self.migrations_dir.exists():
            self.migrations_dir.mkdir(parents=True)
            self.logger.info(f"Created migrations directory: {self.migrations_dir}")

        # Find all Python migration files
        for item in self.migrations_dir.glob("*.py"):
            if item.is_file() and not item.name.startswith("__"):
                migration_files.append(item.name)

        # Sort by filename (which should include timestamps)
        migration_files.sort()
        return migration_files

    def _get_pending_migrations(self) -> list[tuple[str, Any]]:
        """Get a list of pending migrations.

        Returns
        -------
            List of (filename, module) tuples for migrations that need to be applied

        """
        applied_migrations = set(self._get_applied_migrations())
        available_migrations = self._get_available_migrations()

        pending_migrations = []

        for migration_file in available_migrations:
            if migration_file not in applied_migrations:
                # Import the migration module
                module_name = migration_file[:-3]  # Remove .py extension
                try:
                    module_path = f"dewey.core.migrations.migration_files.{module_name}"
                    migration_module = importlib.import_module(module_path)
                    pending_migrations.append((migration_file, migration_module))
                except ImportError as e:
                    self.logger.error(
                        f"Failed to import migration {migration_file}: {e}",
                    )
                    continue

        return pending_migrations

    def _apply_migration(self, migration_file: str, migration_module: Any) -> None:
        """Apply a single migration using a pooled connection and cursor."""
        self.logger.info(f"Applying migration: {migration_file}")

        details = ""
        success = False
        start_time = datetime.now()

        try:
            # Check for required functions
            if not hasattr(migration_module, "migrate"):
                raise AttributeError(
                    f"Migration {migration_file} missing required 'migrate(cursor)' function",
                )

            # Get cursor within a transaction context
            with get_db_cursor(commit=True) as cursor:
                # Pass the cursor to the migration function
                migration_module.migrate(cursor)

            # Mark as successful if no exceptions were raised
            success = True
            duration = (datetime.now() - start_time).total_seconds()
            details = f"Migration applied successfully in {duration:.2f}s"
            self.logger.info(f"Successfully applied migration: {migration_file}")

        except Exception as e:
            details = f"Error: {str(e)}"
            self.logger.exception(f"Failed to apply migration {migration_file}: {e}")
            # The transaction is automatically rolled back by get_db_cursor context manager

        finally:
            # Record the result (success or failure) in the migrations table
            self._record_migration(migration_file, success, details)

    def _record_migration(
        self, migration_name: str, success: bool, details: Optional[str] = None,
    ) -> None:
        """Record the result of a migration attempt in the database."""
        self.logger.debug(f"Recording migration attempt for {migration_name}: Success={success}")
        data = {
            "migration_name": migration_name,
            "applied_at": datetime.now(),  # Record attempt time
            "success": success,
            "details": details or "",
        }
        try:
            # Use insert_row utility
            # This assumes `execute_query` used by `insert_row` handles commit
            insert_row(self.MIGRATIONS_TABLE, data)
            self.logger.debug(f"Recorded migration result for {migration_name}")
        except Exception as e:
            # If logging the migration fails, we have a bigger problem
            self.logger.error(
                f"CRITICAL: Failed to record migration result for {migration_name}: {e}",
            )
            # Decide how to handle this critical failure. Raising might be appropriate.
            # raise

    def create_migration(self, name: str) -> str:
        """Create a new migration file.

        Args:
        ----
            name: A descriptive name for the migration.

        Returns:
        -------
            The path to the created migration file.
        """
        # Ensure the migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Create a timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name.lower().replace(' ', '_')}.py"
        filepath = self.migrations_dir / filename

        # Define template as a regular multiline string first
        raw_template = """\
Migration: {{name}} # Placeholder for format
Timestamp: {{timestamp}} # Placeholder for format
"""


import logging
from psycopg2.extensions import cursor  # Import cursor type hint

logger = logging.getLogger(__name__)


def migrate(cur: cursor):
    \"\"\"Apply the migration steps.

    Args:
    ----
        cur: The database cursor provided by the migration manager.
    \"\"\"
    # Placeholders {name} and {filename} below are NOT formatted by the outer template
    # They are intended to be used within the generated migration file if needed.
    logger.info(\"Applying migration: {name} ({filename}).\")

    # --- Add migration SQL here using cur.execute() ---
    # Example:
    # cur.execute(\"\"\
    #     CREATE TABLE IF NOT EXISTS my_new_table (
    #         id SERIAL PRIMARY KEY,
    #         name VARCHAR(100) NOT NULL
    #     );
    # \"\"\")
    # logger.info(\"Created my_new_table\")

    # --- End migration SQL ---

    logger.info(\"Successfully applied migration: {name} ({filename}).\")

# Optional: Add a rollback function if needed
# def rollback(cur: cursor):
#     \"\"\"Revert the migration steps.
#
#     Args:
#     ----
#         cur: The database cursor.
#     \"\"\"
#     logger.warning(\"Rolling back migration: {name} ({filename}).\")
#     # Add rollback SQL here
#     logger.warning(\"Successfully rolled back migration: {name} ({filename}).\")

"""

        # Format the template with the actual name and timestamp
        template = raw_template.format(name=name, timestamp=timestamp)

        try:
            with open(filepath, "w") as f:
                f.write(template)
            self.logger.info(f"Created new migration file: {filepath}")
            return str(filepath)
        except IOError as e:
            self.logger.error(f"Failed to create migration file {filepath}: {e}")
            raise


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Manage database migrations")
    parser.add_argument("--create", help="Create a new migration with the given name")
    parser.add_argument(
        "--config", help="Path to config file", default="config/dewey.yaml"
    )
    args = parser.parse_args()

    # Load config
    config = {}
    if os.path.exists(args.config):
        with open(args.config) as f:
            config = yaml.safe_load(f) or {}

    # Initialize migration manager
    manager = MigrationManager(config=config)

    if args.create:
        migration_file = manager.create_migration(args.create)
        print(f"Created migration: {migration_file}")
    else:
        # Run pending migrations
        manager.run()
