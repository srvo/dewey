from dewey.core.base_script import BaseScript


class TicDeltaWorkflow(BaseScript):
    """Workflow to process and analyze tick data for delta analysis."""

    def __init__(self):
        """Initializes the TicDeltaWorkflow with configurations."""
        super().__init__(config_section="tic_delta_workflow", requires_db=True)

    def run(self):
        """Executes the tick data processing and delta analysis workflow."""
        self.logger.info("Starting Tic Delta Workflow...")

        if not self.db_conn:
            self.logger.error("Database connection required but not available.")
            return

        try:
            input_table = self.get_config_value("input_table", "default_input_table")
            output_table = self.get_config_value("output_table", "default_output_table")

            self.logger.info(f"Using input table: {input_table}")
            self.logger.info(f"Using output table: {output_table}")

            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {output_table} (
                timestamp TIMESTAMP,
                price FLOAT,
                delta FLOAT
            );
            """
            self.db_conn.execute(create_table_sql)

            insert_query = f"""
            INSERT INTO {output_table} (timestamp, price, delta)
            SELECT timestamp, price, price - LAG(price, 1, price) OVER (ORDER BY timestamp) AS delta
            FROM {input_table}
            """
            self.db_conn.execute(insert_query)
            self.db_conn.commit()

            self.logger.info("Tic Delta Workflow completed successfully.")

        except Exception as e:
            self.logger.error(
                f"An error occurred during Tic Delta Workflow: {e}", exc_info=True
            )
            raise

    def execute(self):
        """Executes the tick data processing and delta analysis workflow."""
        try:
            self.run()
        except Exception as e:
            self.logger.error(f"Error executing TicDeltaWorkflow: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    workflow = TicDeltaWorkflow()
    workflow.execute()
