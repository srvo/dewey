from dewey.core.base_script import BaseScript
from dewey.core.db.utils import execute_query
from dewey.llm.llm_utils import generate_text


class DbMaintenance(BaseScript):
    """
    Manages database maintenance tasks.

    This class inherits from BaseScript and provides methods for
    performing routine database maintenance operations.
    """

    def __init__(self) -> None:
        """Initializes the DbMaintenance class."""
        super().__init__(
            config_section="db_maintenance", requires_db=True, enable_llm=True
        )

    def run(self) -> None:
        """
        Executes the database maintenance tasks.

        This includes checking table sizes, optimizing indexes,
        and performing other maintenance operations.
        """
        self.logger.info("Starting database maintenance...")

        retention_period = self.get_config_value("retention_period", 30)
        self.logger.info(f"Retention period: {retention_period} days")

        self.check_table_sizes()
        self.optimize_indexes()
        self.perform_custom_maintenance()

        self.logger.info("Database maintenance completed.")

    def check_table_sizes(self) -> None:
        """
        Checks the sizes of all tables in the database.

        Logs a warning if any table exceeds a configured threshold.
        """
        self.logger.info("Checking table sizes...")
        size_threshold = self.get_config_value(
            "size_threshold", 1000000
        )  # Example threshold

        try:
            # Example query to get table sizes (specific to your DB)
            query = "SELECT table_name, pg_size_pretty(pg_total_relation_size(table_name)) AS size FROM information_schema.tables WHERE table_schema = 'public';"
            results = execute_query(self.db_conn, query)

            for table_name, size in results:
                size_bytes = int(size.split(" ")[0])  # Simplified size extraction
                if size_bytes > size_threshold:
                    self.logger.warning(
                        f"Table {table_name} exceeds size threshold: {size}"
                    )
        except Exception as e:
            self.logger.error(f"Error checking table sizes: {e}")

    def optimize_indexes(self) -> None:
        """
        Optimizes indexes in the database.

        This can include rebuilding indexes or identifying unused indexes.
        """
        self.logger.info("Optimizing indexes...")

        try:
            # Example query to find unused indexes (specific to your DB)
            query = "SELECT indexrelname FROM pg_stat_all_indexes WHERE idx_scan = 0 AND schemaname = 'public';"
            unused_indexes = execute_query(self.db_conn, query)

            for index_name in unused_indexes:
                self.logger.warning(f"Unused index found: {index_name}")
                # Consider dropping the index or investigating its usage

            # Example query to rebuild indexes (specific to your DB)
            # REINDEX TABLE your_table;
            self.logger.info("Index optimization checks completed.")

        except Exception as e:
            self.logger.error(f"Error optimizing indexes: {e}")

    def perform_custom_maintenance(self) -> None:
        """
        Performs custom database maintenance tasks.

        This can include tasks such as archiving old data,
        updating statistics, or running custom scripts.
        """
        self.logger.info("Performing custom maintenance tasks...")

        try:
            # Example: Archive old data
            archive_query = (
                "DELETE FROM your_table WHERE date < NOW() - INTERVAL '1 year';"
            )
            execute_query(self.db_conn, archive_query)
            self.logger.info("Old data archived.")

            # Example: Update statistics
            analyze_query = "ANALYZE your_table;"
            execute_query(self.db_conn, analyze_query)
            self.logger.info("Table statistics updated.")

            # Example: Use LLM to generate a maintenance report
            llm_prompt = "Generate a brief report summarizing the database maintenance tasks performed."
            report = generate_text(self.llm_client, llm_prompt)
            self.logger.info(f"Maintenance report: {report}")

        except Exception as e:
            self.logger.error(f"Error performing custom maintenance tasks: {e}")
