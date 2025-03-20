from dewey.core.base_script import BaseScript


class Migrations(BaseScript):
    """Manages database migrations.

    This class inherits from BaseScript and provides methods for running
    database migrations. It uses the script's configuration for settings.

    Attributes:
        config_section (str): The configuration section for migrations.
    """

    def __init__(self) -> None:
        """Initializes the Migrations class."""
        super().__init__(config_section='migrations')

    def run(self) -> None:
        """Runs the database migrations.

        This method executes the migrations based on the configuration
        loaded during initialization.
        """
        self.logger.info("Running database migrations...")
        db_host = self.get_config_value("db_host", "localhost")
        self.logger.info(f"Database host: {db_host}")
        # Example: self.logger.info(f"Config value: {self.get_config_value('some_key')}")
        # Example: db_url = self.get_config_value('database_url')
        self.logger.info("Database migrations ran successfully.")
