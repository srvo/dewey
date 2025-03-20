#!/usr/bin/env python3

from dewey.core.base_script import BaseScript
import re
import argparse

class CleanupTables(BaseScript):
    """Script to clean up unnecessary tables while preserving consolidated data."""

    def __init__(self):
        """Function __init__."""
        super().__init__(
            name="cleanup_tables",
            description="Clean up unnecessary tables while preserving consolidated data"
        )

    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up argument parsing for the cleanup script."""
        parser = super().setup_argparse()
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview tables that would be deleted without actually deleting them"
        )
        return parser

    def should_delete_table(self, table_name: str) -> bool:
        """Determine if a table should be deleted based on patterns.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if the table should be deleted, False otherwise
        """
        # Never delete consolidated tables
        if table_name.endswith('_consolidated'):
            return False

        # Patterns for tables to delete
        patterns = [
            r'^other_\d+$',  # Numbered tables
            r'^other_.*_(code|metadata|sections|links)$',  # Documentation sections
            r'^other_test_',  # Test tables
            r'^other_data_test_',  # Data test tables
            r'^other_example_',  # Example tables
            r'^other_.*_table_\d+_\d+$',  # Generated documentation tables
        ]

        return any(re.match(pattern, table_name) for pattern in patterns)

    def run(self):
        """Run the cleanup process."""
        self.logger.info("Starting table cleanup")

        # Get list of all tables
        tables = self.db_engine.list_tables()
        self.logger.info(f"Found {len(tables)} total tables")

        # Identify tables to delete
        tables_to_delete = [table for table in tables if self.should_delete_table(table)]
        self.logger.info(f"Identified {len(tables_to_delete)} tables to delete")

        if self.args.dry_run:
            self.logger.info("DRY RUN - The following tables would be deleted:")
            for table in sorted(tables_to_delete):
                self.logger.info(f"  - {table}")
            return

        # Delete tables
        deleted_count = 0
        error_count = 0
        for table in tables_to_delete:
            try:
                self.db_engine.execute(f"DROP TABLE IF EXISTS {table}")
                self.logger.info(f"Deleted table: {table}")
                deleted_count += 1
            except Exception as e:
                self.logger.error(f"Error deleting table {table}: {str(e)}")
                error_count += 1

        self.logger.info(f"Cleanup complete. Successfully deleted {deleted_count} tables.")
        if error_count > 0:
            self.logger.warning(f"Encountered errors while deleting {error_count} tables.")

if __name__ == "__main__":
    CleanupTables().main() 