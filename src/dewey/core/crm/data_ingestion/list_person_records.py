from dewey.core.base_script import BaseScript


class ListPersonRecords(BaseScript):
    """Lists person records."""

    def __init__(self):
        """Initializes the ListPersonRecords script."""
        super().__init__(config_section="crm", requires_db=True)

    def execute(self) -> None:
        """
        Executes the script to list person records.

        Retrieves person records from the database and logs them.

        Args:
        ----
            None

        Returns:
        -------
            None

        Raises:
        ------
            Exception: If there is an error executing the query.

        """
        try:
            self.logger.info("Starting to list person records...")

            # Example query (replace with your actual query)
            query = "SELECT * FROM persons;"

            with self.db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    records = cursor.fetchall()

            for record in records:
                self.logger.info(f"Record: {record}")

            self.logger.info("Finished listing person records.")

        except Exception as e:
            self.logger.error(f"Error listing person records: {e}")
            raise

    def run(self) -> None:
        """
        Runs the script to list person records.

        Args:
        ----
            None

        Returns:
        -------
            None

        Raises:
        ------
            Exception: If there is an error executing the query.

        """
        try:
            self.logger.info("Starting to list person records...")

            # Example query (replace with your actual query)
            query = "SELECT * FROM persons;"

            with self.db_conn.cursor() as cursor:
                cursor.execute(query)
                records = cursor.fetchall()

            for record in records:
                self.logger.info(f"Record: {record}")

            self.logger.info("Finished listing person records.")

        except Exception as e:
            self.logger.error(f"Error listing person records: {e}")
            raise
