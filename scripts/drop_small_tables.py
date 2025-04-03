#!/usr/bin/env python3
"""Script to identify and drop tables with fewer than N rows."""

from pathlib import Path
from typing import List, Tuple

from dewey.core.base_script import BaseScript


class DropSmallTablesScript(BaseScript):
    """Script to drop tables with row counts below threshold."""

    def __init__(self):
        """Initialize the script."""
        super().__init__(
            name="drop_small_tables", description="Drop tables with fewer than N rows"
        )

    def setup_argparse(self):
        """Set up argument parsing."""
        parser = super().setup_argparse()
        parser.add_argument(
            "--min-rows",
            type=int,
            default=5,
            help="Minimum number of rows to keep a table",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be dropped without actually dropping",
        )
        parser.add_argument(
            "--output", type=Path, help="Path to save list of dropped tables"
        )
        return parser

    def get_table_counts(self) -> list[tuple[str, int]]:
        """Get all tables and their row counts.

        Returns
        -------
            List of (table_name, row_count) tuples

        """
        results = []
        tables = self.db_engine.execute(
            "SELECT table_name FROM duckdb_tables()"
        ).fetchall()

        for (table,) in tables:
            try:
                count = self.db_engine.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
                results.append((table, count))
            except Exception as e:
                self.logger.warning(f"Could not get count for table {table}: {e}")

        return sorted(results, key=lambda x: x[1])

    def drop_tables(self, tables: list[str], dry_run: bool = True) -> None:
        """Drop the specified tables.

        Args:
        ----
            tables: List of table names to drop
            dry_run: If True, only show what would be dropped

        """
        for table in tables:
            try:
                if not dry_run:
                    self.db_engine.execute(f'DROP TABLE IF EXISTS "{table}"')
                self.logger.info(
                    f"{'Would drop' if dry_run else 'Dropped'} table: {table}"
                )
            except Exception as e:
                self.logger.error(f"Error dropping table {table}: {e}")

    def save_results(
        self, dropped_tables: list[tuple[str, int]], output_path: Path
    ) -> None:
        """Save the list of dropped tables.

        Args:
        ----
            dropped_tables: List of (table_name, row_count) tuples
            output_path: Path to save results

        """
        with open(output_path, "w") as f:
            f.write("Table Name,Row Count\n")
            for table, count in dropped_tables:
                f.write(f"{table},{count}\n")

    def run(self) -> None:
        """Run the script."""
        # Get table counts
        self.logger.info("Getting table counts...")
        table_counts = self.get_table_counts()

        # Identify tables to drop
        to_drop = [
            (table, count)
            for table, count in table_counts
            if count < self.args.min_rows
        ]

        # Log summary
        self.logger.info(
            f"\nFound {len(to_drop)} tables with fewer than {self.args.min_rows} rows:"
        )
        for table, count in to_drop:
            self.logger.info(f"  {table}: {count} rows")

        # Confirm if not dry run
        if not self.args.dry_run:
            response = input(f"\nDrop {len(to_drop)} tables? [y/N] ")
            if response.lower() != "y":
                self.logger.info("Aborting.")
                return

        # Drop tables
        self.drop_tables([t[0] for t in to_drop], self.args.dry_run)

        # Save results if requested
        if self.args.output:
            self.save_results(to_drop, self.args.output)
            self.logger.info(f"Saved dropped table list to {self.args.output}")

        # Log completion
        action = "Would have dropped" if self.args.dry_run else "Dropped"
        self.logger.info(f"\n{action} {len(to_drop)} tables")


if __name__ == "__main__":
    DropSmallTablesScript().main()
