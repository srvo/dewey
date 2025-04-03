"""Database migration manager for Dewey.

This module provides tools for managing database migrations, including:
- Tracking applied migrations
- Running migrations in order
- Handling rollbacks
"""

import os
import yaml
import logging
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import duckdb

from dewey.core.base_script import BaseScript


class MigrationManager(BaseScript):
    """Manages database migrations for Dewey.

    This class handles tracking, applying, and rolling back database migrations.
    It ensures migrations are applied in the correct order and only once.
    """

    MIGRATIONS_TABLE = "migrations"

    def __init__(self, config: Dict[str, Any], **kwargs: Any) -> None:
        """Initialize the migration manager.

        Args:
            config: Configuration dictionary
            **kwargs: Additional keyword arguments

        """
        super().__init__(config=config, **kwargs)
        self.migrations_dir = Path(
            self.get_config_value(
                "migrations_directory",
                default=str(Path(__file__).parent / "migration_files"),
            )
        )
        self.conn = None

    def run(self) -> None:
        """Run the migration manager to apply pending migrations."""
        try:
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
            if self.conn:
                self.conn.close()
                self.conn = None

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a database connection.

        Returns:
            A DuckDB connection

        """
        if self.conn is None:
            # Get connection string from config
            db_conn_string = self.get_config_value(
                "database_connection", default="dewey.duckdb"
            )

            # Check if it's a MotherDuck connection
            if db_conn_string.startswith("md:"):
                # Get MotherDuck token
                token = os.environ.get("MOTHERDUCK_TOKEN")
                if not token:
                    token = self.get_config_value("motherduck_token")
                    if token:
                        os.environ["MOTHERDUCK_TOKEN"] = token

            self.logger.info(f"Connecting to database: {db_conn_string}")
            self.conn = duckdb.connect(db_conn_string)

        return self.conn

    def _ensure_migrations_table(self) -> None:
        """Ensure the migrations tracking table exists."""
        conn = self._get_connection()

        # Create migrations table if it doesn't exist
        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.MIGRATIONS_TABLE} (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR NOT NULL,
            applied_at TIMESTAMP NOT NULL,
            success BOOLEAN NOT NULL,
            details TEXT
        )
        """)

        self.logger.info(f"Ensured migrations table '{self.MIGRATIONS_TABLE}' exists.")

    def _get_applied_migrations(self) -> List[str]:
        """Get a list of already applied migrations.

        Returns:
            List of migration filenames that have already been applied

        """
        conn = self._get_connection()

        result = conn.execute(f"""
        SELECT migration_name FROM {self.MIGRATIONS_TABLE}
        WHERE success = TRUE
        ORDER BY applied_at
        """).fetchall()

        return [row[0] for row in result]

    def _get_available_migrations(self) -> List[str]:
        """Get a list of available migration files.

        Returns:
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

    def _get_pending_migrations(self) -> List[Tuple[str, Any]]:
        """Get a list of pending migrations.

        Returns:
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
                        f"Failed to import migration {migration_file}: {e}"
                    )
                    continue

        return pending_migrations

    def _apply_migration(self, migration_file: str, migration_module: Any) -> None:
        """Apply a single migration.

        Args:
            migration_file: The filename of the migration
            migration_module: The imported migration module

        """
        conn = self._get_connection()

        self.logger.info(f"Applying migration: {migration_file}")

        details = ""
        success = False

        try:
            # Check if the migration has the required functions
            if not hasattr(migration_module, "migrate"):
                raise AttributeError(
                    f"Migration {migration_file} missing required 'migrate' function"
                )

            # Apply the migration
            migration_module.migrate(conn)

            # Mark as successful
            success = True
            details = "Migration applied successfully"
            self.logger.info(f"Successfully applied migration: {migration_file}")

        except Exception as e:
            details = f"Error: {str(e)}"
            self.logger.exception(f"Failed to apply migration {migration_file}: {e}")

            # Attempt rollback if available
            if hasattr(migration_module, "rollback"):
                try:
                    self.logger.info(
                        f"Attempting to rollback migration: {migration_file}"
                    )
                    migration_module.rollback(conn)
                    details += "; Rollback successful"
                    self.logger.info(f"Rollback successful for: {migration_file}")
                except Exception as rollback_error:
                    details += f"; Rollback failed: {str(rollback_error)}"
                    self.logger.exception(
                        f"Rollback failed for {migration_file}: {rollback_error}"
                    )

            if not success:
                raise

        finally:
            # Record the migration attempt
            now = datetime.now()
            conn.execute(
                f"""
            INSERT INTO {self.MIGRATIONS_TABLE} (migration_name, applied_at, success, details)
            VALUES (?, ?, ?, ?)
            """,
                [migration_file, now, success, details],
            )

    def create_migration(self, name: str) -> str:
        """Create a new migration file with a timestamp.

        Args:
            name: A descriptive name for the migration

        Returns:
            The path to the created migration file

        """
        # Ensure the migrations directory exists
        if not self.migrations_dir.exists():
            self.migrations_dir.mkdir(parents=True)

        # Create a timestamp for the migration
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Clean the name (remove spaces, lowercase, etc.)
        clean_name = name.lower().replace(" ", "_").replace("-", "_")

        # Create the migration filename
        filename = f"{timestamp}_{clean_name}.py"
        file_path = self.migrations_dir / filename

        # Create the migration file from template
        with open(file_path, "w") as f:
            f.write(
                """\"\"\"
Migration: {name}
Created: {timestamp}
\"\"\"

def migrate(conn):
    \"\"\"Apply the migration.

    Args:
        conn: A DuckDB connection
    \"\"\"
    # Implement the migration here
    conn.execute(\"\"\"
    -- Your SQL here
    \"\"\")

def rollback(conn):
    \"\"\"Rollback the migration.

    Args:
        conn: A DuckDB connection
    \"\"\"
    # Implement the rollback here
    conn.execute(\"\"\"
    -- Your rollback SQL here
    \"\"\")
""".format(name=name, timestamp=datetime.now().isoformat())
            )

        self.logger.info(f"Created new migration file: {file_path}")
        return str(file_path)


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
        with open(args.config, "r") as f:
            config = yaml.safe_load(f) or {}

    # Initialize migration manager
    manager = MigrationManager(config=config)

    if args.create:
        migration_file = manager.create_migration(args.create)
        print(f"Created migration: {migration_file}")
    else:
        # Run pending migrations
        manager.run()
