from dewey.core.base_script import BaseScript


class TicDeltaWorkflow(BaseScript):
    """
    Workflow to process and analyze tick data for delta analysis.
    """

    def __init__(self):
        """
        Initializes the TicDeltaWorkflow with configurations.
        """
        super().__init__(config_section="tic_delta_workflow")

    def run(self):
        """
        Executes the tick data processing and delta analysis workflow.

        This includes:
        1. Fetching data from the database.
        2. Performing delta calculations.
        3. Storing results back in the database.

        Raises:
            Exception: If any error occurs during the workflow execution.
        """
        self.logger.info("Starting Tic Delta Workflow...")

        try:
            # Example: Fetching configuration values
            input_table = self.get_config_value("input_table", "default_input_table")
            output_table = self.get_config_value("output_table", "default_output_table")

            self.logger.info(f"Using input table: {input_table}")
            self.logger.info(f"Using output table: {output_table}")

            # Example: Database operations using utilities from dewey.core.db
            from dewey.core.db.connection import get_connection
            from dewey.core.db.utils import create_table, execute_query

            db_config = self.config.get("database", {})
            with get_connection(db_config) as con:
                # Example: Create a table (replace with actual schema)
                schema = {"timestamp": "TIMESTAMP", "price": "FLOAT", "delta": "FLOAT"}
                create_table(con, output_table, schema)

                # Example: Execute a query (replace with actual query)
                query = f"""
                INSERT INTO {output_table} (timestamp, price, delta)
                SELECT timestamp, price, price - LAG(price, 1, price) OVER (ORDER BY timestamp) AS delta
                FROM {input_table}
                """
                execute_query(con, query)

            self.logger.info("Tic Delta Workflow completed successfully.")

        except Exception as e:
            self.logger.error(f"An error occurred during Tic Delta Workflow: {e}")
            raise


if __name__ == "__main__":
    workflow = TicDeltaWorkflow()
    workflow.execute()
