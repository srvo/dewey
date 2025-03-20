import sys
from typing import Any, Dict

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection
from dewey.llm.llm_utils import LLMClient, get_llm_client


class SyncScript(BaseScript):
    """
    A script for synchronizing data between a source and destination database.
    """

    def __init__(self) -> None:
        """
        Initializes the SyncScript with configurations for database and LLM.
        """
        super().__init__(config_section="sync", requires_db=True, enable_llm=False)
        self.source_db: DatabaseConnection = None
        self.destination_db: DatabaseConnection = None

    def run(self) -> None:
        """
        Executes the data synchronization process.

        This includes connecting to source and destination databases,
        fetching data from the source, transforming it, and loading it
        into the destination.
        """
        try:
            self.logger.info("Starting data synchronization process.")
            self.connect_to_databases()
            self.synchronize_data()
            self.logger.info("Data synchronization process completed successfully.")
        except Exception as e:
            self.logger.error(f"An error occurred during synchronization: {e}", exc_info=True)
            raise

    def connect_to_databases(self) -> None:
        """
        Establishes connections to the source and destination databases
        using configurations from the application settings.
        """
        try:
            self.logger.info("Connecting to source and destination databases.")
            source_db_config = self.get_config_value("source_db")
            destination_db_config = self.get_config_value("destination_db")

            if not source_db_config or not destination_db_config:
                raise ValueError(
                    "Source and destination database configurations must be specified in dewey.yaml."
                )

            self.source_db = get_connection(source_db_config)
            self.destination_db = get_connection(destination_db_config)
            self.logger.info("Successfully connected to both source and destination databases.")
        except Exception as e:
            self.logger.error(f"Failed to connect to databases: {e}", exc_info=True)
            raise

    def synchronize_data(self) -> None:
        """
        Orchestrates the synchronization of data from the source to the
        destination database.

        This involves fetching data, transforming it as necessary, and
        inserting it into the destination database.
        """
        try:
            self.logger.info("Starting data synchronization.")
            # Example: Fetch data from source
            source_data = self.fetch_data_from_source()

            # Example: Transform data
            transformed_data = self.transform_data(source_data)

            # Example: Load data into destination
            self.load_data_into_destination(transformed_data)
            self.logger.info("Data synchronization completed.")
        except Exception as e:
            self.logger.error(f"Data synchronization failed: {e}", exc_info=True)
            raise

    def fetch_data_from_source(self) -> list:
        """
        Fetches data from the source database.

        Returns:
            A list of data records from the source database.

        Raises:
            Exception: If there is an error fetching data from the source.
        """
        try:
            self.logger.info("Fetching data from the source database.")
            # Example SQL query (replace with your actual query)
            query = "SELECT * FROM source_table"
            with self.source_db.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                data = cursor.fetchall()
            self.logger.info(f"Successfully fetched {len(data)} records from the source.")
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch data from source: {e}", exc_info=True)
            raise

    def transform_data(self, data: list) -> list:
        """
        Transforms the fetched data as necessary before loading it into
        the destination database.

        Args:
            data: A list of data records fetched from the source database.

        Returns:
            A list of transformed data records.
        """
        try:
            self.logger.info("Transforming data.")
            transformed_data = []
            for record in data:
                # Example transformation (replace with your actual transformation logic)
                transformed_record = {
                    "id": record[0],
                    "value": record[1] * 2,
                }
                transformed_data.append(transformed_record)
            self.logger.info(f"Successfully transformed {len(transformed_data)} records.")
            return transformed_data
        except Exception as e:
            self.logger.error(f"Data transformation failed: {e}", exc_info=True)
            raise

    def load_data_into_destination(self, data: list) -> None:
        """
        Loads the transformed data into the destination database.

        Args:
            data: A list of transformed data records to load into the
                destination database.
        """
        try:
            self.logger.info("Loading data into the destination database.")
            # Example SQL query (replace with your actual query)
            query = "INSERT INTO destination_table (id, value) VALUES (%s, %s)"
            with self.destination_db.connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, [(record["id"], record["value"]) for record in data])
                conn.commit()
            self.logger.info(f"Successfully loaded {len(data)} records into the destination.")
        except Exception as e:
            self.logger.error(f"Failed to load data into destination: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    sync_script = SyncScript()
    sync_script.execute()
