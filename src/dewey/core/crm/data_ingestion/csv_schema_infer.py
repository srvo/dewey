from dewey.core.base_script import BaseScript
from dewey.core.db.utils import create_table, insert_data
from dewey.llm.llm_utils import generate_schema_from_data


class CSVInferSchema(BaseScript):
    """Infers schema from CSV file and creates a table in the database."""

    def __init__(self, config_section: str | None = None) -> None:
        """
        Initializes the CSVInferSchema class.

        Args:
        ----
            config_section (Optional[str]): The section in the config file to use.

        """
        super().__init__(
            name="CSV Schema Inference",
            description="Infers schema from CSV file and creates a table in the database.",
            config_section=config_section,
            requires_db=True,
            enable_llm=True,
        )

    def run(self) -> None:
        """Runs the schema inference and table creation process."""
        csv_file_path = self.get_config_value("csv_file_path")
        table_name = self.get_config_value("table_name")

        if not csv_file_path or not table_name:
            self.logger.error("CSV file path or table name not provided in config.")
            raise ValueError("CSV file path and table name must be provided in config.")

        try:
            with open(csv_file_path, encoding="utf-8") as csvfile:
                csv_data = csvfile.read()

            # Infer schema using LLM
            schema = self._infer_schema(csv_data)

            # Create table in database
            self._create_table(table_name, schema)

            # Insert data into table
            self._insert_data(csv_file_path, table_name, schema)

            self.logger.info(
                f"Successfully created table {table_name} from {csv_file_path}",
            )

        except Exception as e:
            self.logger.error(f"Error processing CSV file: {e}")
            raise

    def _infer_schema(self, csv_data: str) -> dict[str, str]:
        """
        Infers the schema of the CSV data using an LLM.

        Args:
        ----
            csv_data (str): The CSV data as a string.

        Returns:
        -------
            Dict[str, str]: A dictionary representing the schema, where keys are column names and values are data types.

        Raises:
        ------
            Exception: If there is an error during schema inference.

        """
        try:
            self.logger.info("Inferring schema using LLM...")
            schema = generate_schema_from_data(csv_data, llm_client=self.llm_client)
            self.logger.info("Schema inferred successfully.")
            return schema
        except Exception as e:
            self.logger.error(f"Error inferring schema: {e}")
            raise

    def _create_table(self, table_name: str, schema: dict[str, str]) -> None:
        """
        Creates a table in the database based on the inferred schema.

        Args:
        ----
            table_name (str): The name of the table to create.
            schema (Dict[str, str]): A dictionary representing the schema.

        Raises:
        ------
            Exception: If there is an error during table creation.

        """
        try:
            self.logger.info(f"Creating table {table_name}...")
            create_table(self.db_conn, table_name, schema)
            self.logger.info(f"Table {table_name} created successfully.")
        except Exception as e:
            self.logger.error(f"Error creating table: {e}")
            raise

    def _insert_data(
        self, csv_file_path: str, table_name: str, schema: dict[str, str],
    ) -> None:
        """
        Inserts data from the CSV file into the specified table.

        Args:
        ----
            csv_file_path (str): The path to the CSV file.
            table_name (str): The name of the table to insert data into.
            schema (Dict[str, str]): A dictionary representing the schema.

        Raises:
        ------
            Exception: If there is an error during data insertion.

        """
        try:
            self.logger.info(f"Inserting data into table {table_name}...")
            insert_data(self.db_conn, csv_file_path, table_name, schema)
            self.logger.info(f"Data inserted into table {table_name} successfully.")
        except Exception as e:
            self.logger.error(f"Error inserting data: {e}")
            raise


if __name__ == "__main__":
    script = CSVInferSchema()
    script.execute()
