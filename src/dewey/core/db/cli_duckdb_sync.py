#!/usr/bin/env python
"""Script to synchronize between local DuckDB and MotherDuck.

This script can be run to manually sync data between a local DuckDB
database and a MotherDuck (cloud) instance.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from dewey.core.base_script import BaseScript
from dewey.core.db.sync import get_duckdb_sync


class SyncDuckDBScript(BaseScript):
    """Script to synchronize between local DuckDB and MotherDuck."""

    def __init__(self) -> None:
        """Initialize the SyncDuckDBScript."""
        super().__init__(config_section="db")

        # Parse command line arguments
        self.args = self._parse_args()

        # Initialize sync instance
        self.sync = None

    def _parse_args(self) -> argparse.Namespace:
        """Parse command line arguments.

        Returns:
            Parsed arguments

        """
        parser = argparse.ArgumentParser(
            description="Sync between local DuckDB and MotherDuck",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

        parser.add_argument(
            "--local-db",
            help="Path to the local DuckDB file",
            default=str(Path.cwd() / "dewey.duckdb"),
            type=str,
        )

        parser.add_argument(
            "--md-db", help="MotherDuck database name", default="dewey", type=str
        )

        parser.add_argument(
            "--token",
            help="MotherDuck token (defaults to MOTHERDUCK_TOKEN env var)",
            default=os.environ.get("MOTHERDUCK_TOKEN"),
            type=str,
        )

        parser.add_argument(
            "--direction",
            help="Sync direction",
            choices=["down", "up", "both"],
            default="both",
            type=str,
        )

        parser.add_argument(
            "--tables", help="Specific tables to sync (comma-separated)", type=str
        )

        parser.add_argument(
            "--exclude", help="Tables to exclude from sync (comma-separated)", type=str
        )

        parser.add_argument(
            "--monitor",
            help="Monitor for changes and sync continuously",
            action="store_true",
        )

        parser.add_argument(
            "--interval",
            help="Sync interval in seconds when monitoring",
            default=60,
            type=int,
        )

        parser.add_argument(
            "--verbose", help="Enable verbose logging", action="store_true"
        )

        return parser.parse_args()

    def execute(self) -> None:
        """Execute the sync script.

        This method replaces the legacy run() method. It configures logging,
        initializes the sync instance, parses table lists, and performs the
        sync operation based on the specified direction and monitoring mode.
        """
        # Configure logging level
        if self.args.verbose:
            import logging

            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Verbose logging enabled")

        # Initialize sync instance
        self.logger.info(
            f"Initializing sync between local DB {self.args.local_db} and MotherDuck DB {self.args.md_db}"
        )

        try:
            self.sync = get_duckdb_sync(
                local_db_path=self.args.local_db,
                motherduck_db=self.args.md_db,
                motherduck_token=self.args.token,
                auto_sync=False,  # Disable auto-sync for manual control
            )

            # Parse table lists
            tables_to_sync = (
                self._parse_table_list(self.args.tables) if self.args.tables else None
            )
            tables_to_exclude = (
                self._parse_table_list(self.args.exclude) if self.args.exclude else []
            )

            # Perform sync based on direction
            if self.args.monitor:
                self._run_monitor_mode(tables_to_sync, tables_to_exclude)
            else:
                success = self._run_sync(
                    self.args.direction, tables_to_sync, tables_to_exclude
                )
                if not success:
                    self.logger.error("Sync failed")
                    sys.exit(1)

        except Exception as e:
            self.logger.error(f"Error during sync: {e}")
            sys.exit(1)
        finally:
            if self.sync:
                self.sync.close()

    def run(self) -> None:
        """Run the sync script."""
        # Configure logging level
        if self.args.verbose:
            import logging

            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Verbose logging enabled")

        # Initialize sync instance
        self.logger.info(
            f"Initializing sync between local DB {self.args.local_db} and MotherDuck DB {self.args.md_db}"
        )

        try:
            self.sync = get_duckdb_sync(
                local_db_path=self.args.local_db,
                motherduck_db=self.args.md_db,
                motherduck_token=self.args.token,
                auto_sync=False,  # Disable auto-sync for manual control
            )

            # Parse table lists
            tables_to_sync = (
                self._parse_table_list(self.args.tables) if self.args.tables else None
            )
            tables_to_exclude = (
                self._parse_table_list(self.args.exclude) if self.args.exclude else []
            )

            # Perform sync based on direction
            if self.args.monitor:
                self._run_monitor_mode(tables_to_sync, tables_to_exclude)
            else:
                success = self._run_sync(
                    self.args.direction, tables_to_sync, tables_to_exclude
                )
                if not success:
                    self.logger.error("Sync failed")
                    sys.exit(1)

        except Exception as e:
            self.logger.error(f"Error during sync: {e}")
            sys.exit(1)
        finally:
            if self.sync:
                self.sync.close()

    def _parse_table_list(self, table_str: str) -> list[str]:
        """Parse a comma-separated list of tables.

        Args:
            table_str: Comma-separated list of table names

        Returns:
            List of table names

        """
        return [t.strip() for t in table_str.split(",") if t.strip()]

    def _run_sync(
        self,
        direction: str,
        tables: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> bool:
        """Run a sync operation.

        Args:
            direction: Sync direction ('up', 'down', or 'both')
            tables: Specific tables to sync, or None for all tables
            exclude: Tables to exclude from sync

        Returns:
            True if sync was successful, False otherwise

        """
        success = True

        if exclude is None:
            exclude = []

        if direction in ("down", "both"):
            self.logger.info("Syncing from MotherDuck to local...")

            if tables:
                # Sync specific tables
                for table in tables:
                    if table in exclude:
                        self.logger.info(f"Skipping excluded table: {table}")
                        continue

                    self.logger.info(f"Syncing table {table} from MotherDuck to local")
                    table_success = self.sync.sync_table_to_local(table)
                    if not table_success:
                        self.logger.error(
                            f"Failed to sync table {table} from MotherDuck to local"
                        )
                        success = False
            else:
                # Sync all tables except excluded ones
                md_tables = self.sync.list_tables(self.sync.motherduck_conn)
                for table in md_tables:
                    if table in exclude:
                        self.logger.info(f"Skipping excluded table: {table}")
                        continue

                    if table.startswith("sqlite_") or table.startswith("dewey_sync_"):
                        self.logger.debug(f"Skipping system table: {table}")
                        continue

                    self.logger.info(f"Syncing table {table} from MotherDuck to local")
                    table_success = self.sync.sync_table_to_local(table)
                    if not table_success:
                        self.logger.error(
                            f"Failed to sync table {table} from MotherDuck to local"
                        )
                        success = False

        if direction in ("up", "both"):
            self.logger.info("Syncing from local to MotherDuck...")

            if tables:
                # Sync specific tables
                for table in tables:
                    if table in exclude:
                        self.logger.info(f"Skipping excluded table: {table}")
                        continue

                    self.logger.info(f"Syncing table {table} from local to MotherDuck")
                    table_success = self.sync.sync_table_to_motherduck(table)
                    if not table_success:
                        self.logger.error(
                            f"Failed to sync table {table} from local to MotherDuck"
                        )
                        success = False
            else:
                # Sync all tables except excluded ones
                local_tables = self.sync.list_tables(self.sync.local_conn)
                for table in local_tables:
                    if table in exclude:
                        self.logger.info(f"Skipping excluded table: {table}")
                        continue

                    if table.startswith("sqlite_") or table.startswith("dewey_sync_"):
                        self.logger.debug(f"Skipping system table: {table}")
                        continue

                    self.logger.info(f"Syncing table {table} from local to MotherDuck")
                    table_success = self.sync.sync_table_to_motherduck(table)
                    if not table_success:
                        self.logger.error(
                            f"Failed to sync table {table} from local to MotherDuck"
                        )
                        success = False

        return success

    def _run_monitor_mode(
        self, tables: list[str] | None = None, exclude: list[str] | None = None
    ) -> None:
        """Run in monitor mode, continuously syncing changes.

        Args:
            tables: Specific tables to sync, or None for all tables
            exclude: Tables to exclude from sync

        """
        self.logger.info(
            f"Starting monitor mode with {self.args.interval} second interval"
        )

        try:
            while True:
                self.logger.info("Running sync...")
                self._run_sync(self.args.direction, tables, exclude)

                self.logger.info(f"Sleeping for {self.args.interval} seconds...")
                time.sleep(self.args.interval)
        except KeyboardInterrupt:
            self.logger.info("Monitor mode stopped by user")


def main():
    """Main entry point for the script."""
    script = SyncDuckDBScript()
    script.run()


if __name__ == "__main__":
    main()
