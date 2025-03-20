from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection, get_motherduck_connection
from dewey.core.db.utils import create_table, execute_query
from dewey.llm.llm_utils import generate_text
import logging
from typing import Any, Dict, Optional


class CsvContactIntegration(BaseScript):
    """
    A class for integrating contacts from a CSV file into the CRM system.

    This class inherits from BaseScript and provides methods for
    reading contact data from a CSV file and integrating it into
    the CRM system.
    """

    def __init__(self) -> None:
        """
        Initializes the CsvContactIntegration class.
        """
        super().__init__(config_section='csv_contact_integration', requires_db=True)

    def run(self) -> None:
        """
        Runs the CSV contact integration process.

        This method orchestrates the CSV contact integration process,
        including reading the file path from the configuration,
        processing the CSV file, and handling any exceptions.

        Args:
            None

        Returns:
            None

        Raises:
            FileNotFoundError: If the specified CSV file does not exist.
            Exception: If any error occurs during the integration process.
        """
        self.logger.info("Starting CSV contact integration...")
        try:
            # Access the file path from the configuration
            file_path = self.get_config_value("file_path", "default_path.csv")
            self.logger.info(f"Using file path: {file_path}")

            # Process the CSV file
            self.process_csv(file_path)

            self.logger.info("CSV contact integration completed.")

        except FileNotFoundError as e:
            self.logger.error(f"File not found: {e}")
            raise
        except Exception as e:
            self.logger.error(f"An error occurred during CSV contact integration: {e}")
            raise

    def process_csv(self, file_path: str) -> None:
        """
        Processes the CSV file and integrates contacts into the CRM system.

        This method reads the CSV file from the specified path, extracts
        contact data, and integrates it into the CRM system.

        Args:
            file_path: The path to the CSV file.

        Returns:
            None

        Raises:
            Exception: If any error occurs during CSV processing.
        """
        self.logger.info(f"Processing CSV file: {file_path}")
        try:
            # Example: Read the CSV file using pandas (you might need to install it)
            import pandas as pd

            df = pd.read_csv(file_path)
            
            # Check if the dataframe is empty
            if df.empty:
                self.logger.info("CSV file is empty or contains only headers.")
            else:
                # Example: Iterate over rows and insert data into the database
                for index, row in df.iterrows():
                    # Extract contact data from the row
                    contact_data = row.to_dict()

                    # Example: Insert contact data into the database
                    self.insert_contact(contact_data)

            self.logger.info("CSV processing completed.")

        except Exception as e:
            self.logger.error(f"An error occurred during CSV processing: {e}")
            raise

    def insert_contact(self, contact_data: Dict[str, Any]) -> None:
        """
        Inserts contact data into the CRM system.

        This method takes a dictionary of contact data and inserts it
        into the appropriate table in the CRM database.

        Args:
            contact_data: A dictionary containing contact data.

        Returns:
            None

        Raises:
            Exception: If any error occurs during contact insertion.
        """
        try:
            # Validate data
            if not contact_data:
                raise ValueError("Empty contact data")
                
            # Validate data types - ensure all values can be safely converted to strings
            for key, value in contact_data.items():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    raise TypeError(f"Unsupported data type for {key}: {type(value)}")
            
            # Example: Insert contact data into the database
            table_name = "contacts"  # Replace with your actual table name
            columns = ", ".join(contact_data.keys())
            values = ", ".join([f"'{value}'" for value in contact_data.values()])
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"

            # Execute the query using the database connection
            self.db_conn.execute(query)

            self.logger.info(f"Inserted contact: {contact_data}")

        except Exception as e:
            self.logger.error(f"An error occurred during contact insertion: {e}")
            raise


if __name__ == "__main__":
    integration = CsvContactIntegration()
    integration.run()
