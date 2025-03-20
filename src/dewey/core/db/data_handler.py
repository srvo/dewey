from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from dewey.core.db.utils import create_table, execute_query


class DataHandler(BaseScript):
    """
    A comprehensive data processing class that combines initialization and
    representation functionalities.

    This class provides a streamlined way to represent and initialize data
    objects, handling potential edge cases and adhering to modern Python
    conventions.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes a DataHandler object.

        Args:
            name: The name of the data processor.

        Raises:
            TypeError: If the provided name is not a string.

        Examples:
            >>> processor = DataHandler("MyProcessor")
            >>> processor.name
            "MyProcessor"
        """
        super().__init__(config_section="db")
        if not isinstance(name, str):
            raise TypeError("Name must be a string.")
        self.name = name
        self.logger.info(f"DataHandler initialized with name: {name}")

    def __repr__(self) -> str:
        """
        Returns a string representation of the DataHandler object.

        This representation is suitable for debugging and logging purposes.

        Returns:
            A string representing the DataHandler object in the format
            "DataHandler(name='<name>')".

        Examples:
            >>> processor = DataHandler("MyProcessor")
            >>> repr(processor)
            "DataHandler(name='MyProcessor')"
        """
        return f"DataHandler(name='{self.name}')"

    def run(self) -> None:
        """
        Runs the DataHandler script.
        """
        self.logger.info("Running DataHandler script...")

        # Example Usage (demonstrates the functionality and edge case handling)
        # Valid initialization
        processor1 = DataHandler("MyDataProcessor")
        self.logger.info(f"Processor 1: {processor1}")

        # Invalid initialization (TypeError)
        try:
            DataHandler(123)
        except TypeError as e:
            self.logger.error(f"Error initializing processor 2: {e}")

        # Representation check
        processor3 = DataHandler("AnotherProcessor")
        self.logger.info(f"Representation of processor 3: {repr(processor3)}")

        # Example database operation (replace with your actual logic)
        try:
            db_config = self.get_config_value("test_database_config")
            if db_config is None:
                raise ValueError("Database configuration not found.")

            with get_connection(db_config) as conn:
                # Example: Create a table (replace with your actual schema)
                table_name = "example_table"
                schema = {"id": "INTEGER", "name": "VARCHAR"}
                create_table(conn, table_name, schema)

                # Example: Insert data (replace with your actual data)
                data = {"id": 1, "name": "Example Data"}
                insert_query = f"INSERT INTO {table_name} (id, name) VALUES (?, ?)"
                execute_query(conn, insert_query, (data["id"], data["name"]))

                self.logger.info(
                    f"Successfully created table and inserted data into {table_name}"
                )

        except Exception as e:
            self.logger.error(f"Error during database operation: {e}")

        self.logger.info("DataHandler script completed.")


# Example Usage (demonstrates the functionality and edge case handling)
if __name__ == "__main__":
    script = DataHandler("MainDataHandler")
    script.run()
