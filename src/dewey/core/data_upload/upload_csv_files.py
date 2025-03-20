from dewey.core.base_script import BaseScript
from dewey.core.db.connection import DatabaseConnection, get_connection, get_motherduck_connection
from dewey.core.db import utils as db_utils
from dewey.llm import llm_utils
import ibis
import pandas as pd
from typing import Optional


class UploadCsvFiles(BaseScript):
    """
    A class for uploading CSV files to a database.
    """

    def __init__(self):
        """
        Initializes the UploadCsvFiles class, inheriting from BaseScript.
        """
        super().__init__(config_section='upload_csv_files', requires_db=True)

    def run(self) -> None:
        """
        Runs the CSV file upload process.

        This method orchestrates the process of reading a CSV file,
        inferring its schema, creating a table in the database (if it
        doesn't exist), and uploading the data into the table.

        Raises:
            FileNotFoundError: If the specified CSV file does not exist.
            Exception: If any error occurs during the CSV file upload process.
        """
        self.logger.info("Starting CSV file upload process.")

        try:
            # 1. Get configuration values
            file_path: str = self.get_config_value("file_path")
            table_name: str = self.get_config_value("table_name", "uploaded_csv_data")
            motherduck_token: Optional[str] = self.get_config_value("motherduck_token")

            # 2. Validate file path
            if not file_path:
                raise ValueError("File path must be specified in the configuration.")

            # 3. Read CSV file into a Pandas DataFrame
            self.logger.info(f"Reading CSV file from: {file_path}")
            df: pd.DataFrame = pd.read_csv(file_path)

            # 4. Get an Ibis connection
            con: ibis.backends.base.BaseBackend = self.db_conn

            # 5. Check if the table exists
            if table_name in con.list_tables():
                self.logger.info(f"Table '{table_name}' already exists in the database.")
            else:
                # 6. Create the table if it doesn't exist
                self.logger.info(f"Creating table '{table_name}' in the database.")
                db_utils.create_table_from_dataframe(con, table_name, df)

            # 7. Insert data into the table
            self.logger.info(f"Inserting data into table '{table_name}'.")
            db_utils.insert_dataframe(con, table_name, df)

            self.logger.info("CSV file upload process completed successfully.")

        except FileNotFoundError as e:
            self.logger.error(f"File not found: {e}")
            raise
        except Exception as e:
            self.logger.error(f"An error occurred during CSV file upload: {e}")
            raise


if __name__ == "__main__":
    uploader = UploadCsvFiles()
    uploader.execute()
