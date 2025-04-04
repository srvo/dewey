from typing import Any

from dewey.core.base_script import BaseScript


class AnalyzeTables(BaseScript):
    """
    Analyzes database tables.

    This module analyzes the tables in the database and performs
    maintenance tasks as needed.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the AnalyzeTables module."""
        super().__init__(*args, **kwargs)

    def execute(self) -> None:
        """
        Executes the table analysis and maintenance process.

        This method connects to the database and analyzes each table to
        provide statistics such as row count and size.
        """
        self.logger.info("Starting table analysis...")

        try:
            with self.db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get all table names in the database
                    cursor.execute(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_type = 'BASE TABLE';
                        """,
                    )
                    tables = [table[0] for table in cursor.fetchall()]

                    for table in tables:
                        self.logger.info(f"Analyzing table: {table}")

                        # Get the row count for the table
                        cursor.execute(f"SELECT COUNT(*) FROM {table};")
                        row_count = cursor.fetchone()[0]
                        self.logger.info(f"Table {table} has {row_count} rows.")

                        # Get the table size
                        cursor.execute(
                            f"""
                            SELECT pg_size_pretty(pg_total_relation_size('{table}'));
                            """,
                        )
                        table_size = cursor.fetchone()[0]
                        self.logger.info(f"Table {table} size: {table_size}")

        except Exception as e:
            self.logger.error(f"Error analyzing tables: {e}")
            raise

        self.logger.info("Table analysis complete.")

    def analyze_tables(self) -> None:
        """Analyzes each table in the database."""
        self.logger.info("Analyzing tables...")
        # Add your table analysis logic here
        self.logger.info("Tables analyzed.")


if __name__ == "__main__":
    # Example usage (replace with your actual initialization)
    script = AnalyzeTables()
    script.execute()
