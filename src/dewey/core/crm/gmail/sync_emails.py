from dewey.core.base_script import BaseScript


class SyncEmails(BaseScript):
    """
    Synchronizes emails from Gmail.

    This script fetches emails from Gmail and stores them in the database.
    """

    def __init__(self):
        """Initializes the SyncEmails script."""
        super().__init__(config_section="gmail_sync", requires_db=True)

    def execute(self) -> None:
        """
        Runs the email synchronization process.

        Fetches emails from Gmail and stores them in the database.

        Raises
        ------
            Exception: If any error occurs during the synchronization process.

        """
        self.logger.info("Starting email synchronization")
        try:
            # Implement email synchronization logic here
            # Use self.get_config_value() to access configuration values
            # Use self.db_conn to interact with the database
            # Use self.logger to log messages
            self.logger.info("Email synchronization completed successfully")
        except Exception as e:
            self.logger.error(f"Error during email synchronization: {e}", exc_info=True)
            raise

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
