from dewey.core.base_script import BaseScript


class ConsolidateEmailTables(BaseScript):
    """
    Consolidates email tables.

    This script performs the consolidation of email tables, adhering to Dewey conventions
    for configuration, logging, and execution.
    """

    def __init__(self):
        """Initializes the ConsolidateEmailTables script."""
        super().__init__(config_section='consolidate_email_tables')

    def run(self) -> None:
        """
        Executes the email table consolidation process.
        """
        self.logger.info("Starting email table consolidation...")

        # Example of accessing configuration values
        some_config_value = self.get_config_value('some_config_key', 'default_value')
        self.logger.debug(f"Using some_config_value: {some_config_value}")

        # Add your consolidation logic here
        self.logger.info("Email table consolidation completed.")


if __name__ == "__main__":
    script = ConsolidateEmailTables()
    script.run()
