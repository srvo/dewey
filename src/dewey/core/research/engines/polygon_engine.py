from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_motherduck_connection
from dewey.core.db.utils import create_table, execute_query
from dewey.llm.llm_utils import call_llm


class PolygonEngine(BaseScript):
    """Engine for interacting with the Polygon API."""

    def __init__(self, config_section: str = "polygon_engine") -> None:
        """Initializes the PolygonEngine.

        Args:
            config_section (str): Section in dewey.yaml to load for this engine.

        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """Executes the main logic of the Polygon engine."""
        self.logger.info("Polygon engine started.")

        api_key = self.get_config_value("api_key")
        if not api_key:
            self.logger.error("Polygon API key not found in configuration.")
            return

        # Example database interaction (replace with your actual logic)
        try:
            with get_motherduck_connection() as conn:
                # Example: Create a table (replace with your actual schema)
                table_name = "polygon_data"
                schema = {
                    "ticker": "VARCHAR",
                    "timestamp": "TIMESTAMP",
                    "price": "DOUBLE",
                }
                create_table(conn, table_name, schema)

                # Example: Insert data (replace with your actual data)
                data = {
                    "ticker": "AAPL",
                    "timestamp": "2024-01-01",
                    "price": 170.00,
                }
                insert_query = (
                    f"INSERT INTO {table_name} ({', '.join(data.keys())}) "
                    f"VALUES ({', '.join(['?' for _ in data.values()])})"
                )
                execute_query(conn, insert_query, list(data.values()))

                self.logger.info(
                    f"Successfully created table {table_name} and inserted sample data."
                )

        except Exception as e:
            self.logger.error(f"Error interacting with the database: {e}")
            return

        # Example LLM interaction (replace with your actual logic)
        try:
            prompt = "Summarize the current market conditions for AAPL."
            response = call_llm(prompt)  # Assuming a default LLM client is configured
            self.logger.info(f"LLM Response: {response}")
        except Exception as e:
            self.logger.error(f"Error interacting with the LLM: {e}")
            return

        self.logger.info("Polygon engine finished.")
