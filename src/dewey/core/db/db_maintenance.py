"""Database maintenance utilities.

This module provides functionality for maintaining and optimizing
the database, including checking table sizes, analyzing tables,
and performing optimization.
"""

from typing import Dict, List, Optional

from dewey.core.base_script import BaseScript


class DbMaintenance(BaseScript):
    """Class for database maintenance operations.

    This class provides methods to perform various maintenance tasks
    on the database, such as checking table sizes, analyzing tables,
    and optimizing tables.
    """

    def __init__(self) -> None:
        """Initialize the DbMaintenance class."""
        self.name = "DbMaintenance"
        super().__init__(
            name=self.name,
            config_section="db_maintenance",
            requires_db=True,
            enable_llm=True,
        )

    def run(self) -> None:
        """Run the database maintenance operations.

        This method performs various maintenance tasks on the database,
        including checking table sizes, analyzing tables, and optimizing tables.
        The check interval can be configured in the configuration file.
        """
        self.logger.info("Starting database maintenance...")

        # Get the check interval from config or use default (30 days)
        check_interval = self.get_config_value("check_interval", 30)
        self.logger.info(f"Using check interval of {check_interval} days")

        # Perform maintenance tasks
        self.check_table_sizes()
        self.analyze_tables()
        self.optimize_tables()

        self.logger.info("Database maintenance completed")

    def check_table_sizes(self) -> dict[str, int]:
        """Check the sizes of all tables in the database.

        Returns:
            Dictionary mapping table names to their sizes in bytes

        """
        self.logger.info("Checking table sizes...")

        try:
            # Get the list of tables
            tables = self.get_table_list()

            # Dictionary to store table sizes
            table_sizes = {}

            # Query to get table size
            for table in tables:
                query = f"SELECT COUNT() AS row_count FROM {table}"
                result = self.db_conn.execute(query).fetchall()
                row_count = result[0][0] if result else 0
                table_sizes[table] = row_count
                self.logger.debug(f"Table {table}: {row_count} rows")

            self.logger.info(f"Checked sizes for {len(tables)} tables")
            return table_sizes

        except Exception as e:
            self.logger.error(f"Error checking table sizes: {e}")
            return {}

    def analyze_tables(self, tables: list[str] | None = None) -> None:
        """Analyze tables to update statistics.

        Args:
            tables: Optional list of tables to analyze. If None, all tables are analyzed.

        """
        self.logger.info("Analyzing tables...")

        try:
            # If no tables are specified, get all tables
            if tables is None:
                tables = self.get_table_list()

            # Analyze each table
            for table in tables:
                self.logger.debug(f"Analyzing table {table}")
                self.db_conn.execute(f"ANALYZE {table}")

            self.logger.info(f"Analyzed {len(tables)} tables")

        except Exception as e:
            self.logger.error(f"Error analyzing tables: {e}")

    def optimize_tables(self, tables: list[str] | None = None) -> None:
        """Optimize tables for better performance.

        Args:
            tables: Optional list of tables to optimize. If None, all tables are optimized.

        """
        self.logger.info("Optimizing tables...")

        try:
            # If no tables are specified, get all tables
            if tables is None:
                tables = self.get_table_list()

            # Optimize each table
            for table in tables:
                self.logger.debug(f"Optimizing table {table}")
                self.db_conn.execute(f"VACUUM {table}")

            self.logger.info(f"Optimized {len(tables)} tables")

        except Exception as e:
            self.logger.error(f"Error optimizing tables: {e}")

    def get_table_list(self) -> list[str]:
        """Get a list of all tables in the database.

        Returns:
            List of table names

        """
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        result = self.db_conn.execute(query).fetchall()
        return [row[0] for row in result]
