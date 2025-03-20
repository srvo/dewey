from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_motherduck_connection
from dewey.llm.llm_utils import call_llm
import ibis.expr.types as ir


class CheckData(BaseScript):
    """
    A class for checking data, adhering to Dewey project conventions.
    """

    def __init__(self):
        """
        Initializes the CheckData class, inheriting from BaseScript.
        """
        super().__init__(config_section="check_data", requires_db=True, enable_llm=True)

    def run(self) -> None:
        """
        Runs the data checking process.

        This method orchestrates the data checking process, including:
        1. Logging the start of the data check.
        2. Accessing configuration values.
        3. Performing data checking operations using database utilities and LLM calls.
        4. Logging the completion of the data check.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: If any error occurs during the data checking process.
        """
        self.logger.info("Starting data check...")

        try:
            # Access configuration values using self.get_config_value()
            data_path = self.get_config_value("data_path")
            table_name = self.get_config_value("table_name", "default_table")

            self.logger.info(f"Data path: {data_path}, Table name: {table_name}")

            # Example database operation (replace with your actual logic)
            # Assuming you have a method to get an Ibis table expression
            data = self._load_data(data_path)

            # Example LLM call (replace with your actual logic)
            analysis_result = self._analyze_data(data)

            self.logger.info(f"Data analysis result: {analysis_result}")

            # Example database table creation and insertion
            self._create_and_insert_table(table_name, data)

            self.logger.info("Data check complete.")

        except Exception as e:
            self.logger.error(f"Error during data check: {e}", exc_info=True)
            raise

    def _load_data(self, data_path: str) -> ir.Table:
        """
        Loads data from the specified path using Ibis.

        Args:
            data_path: The path to the data file.

        Returns:
            An Ibis table expression representing the loaded data.

        Raises:
            FileNotFoundError: If the data file does not exist.
            Exception: If any error occurs during data loading.
        """
        try:
            self.logger.info(f"Loading data from {data_path}")
            # Example: Load data from a CSV file using Ibis
            # Replace with your actual data loading logic
            con = get_motherduck_connection()
            data = con.read_csv(data_path)
            return data
        except FileNotFoundError:
            self.logger.error(f"Data file not found: {data_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading data: {e}", exc_info=True)
            raise

    def _analyze_data(self, data: ir.Table) -> str:
        """
        Analyzes the data using an LLM.

        Args:
            data: An Ibis table expression representing the data to analyze.

        Returns:
            A string containing the analysis result from the LLM.

        Raises:
            Exception: If any error occurs during LLM call.
        """
        try:
            self.logger.info("Analyzing data using LLM...")
            # Example: Create a prompt for the LLM
            prompt = f"Analyze the following data: {data.head()}"

            # Call the LLM using llm_utils
            response = call_llm(prompt, self.config.get("llm", {}))
            return response

        except Exception as e:
            self.logger.error(f"Error during LLM call: {e}", exc_info=True)
            raise

    def _create_and_insert_table(self, table_name: str, data: ir.Table) -> None:
        """
        Creates a table in the database and inserts data into it.

        Args:
            table_name: The name of the table to create.
            data: An Ibis table expression representing the data to insert.

        Returns:
            None

        Raises:
            Exception: If any error occurs during table creation or data insertion.
        """
        try:
            self.logger.info(f"Creating table {table_name} and inserting data...")
            # Example: Create a table using utils.create_table
            # Replace with your actual table creation logic
            con = get_motherduck_connection()
            con.create_table(table_name, data=data)

        except Exception as e:
            self.logger.error(f"Error creating or inserting table: {e}", exc_info=True)
            raise
