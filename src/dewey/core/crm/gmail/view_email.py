from dewey.core.base_script import BaseScript


class ViewEmail(BaseScript):
    """A class to view emails."""

    def __init__(self):
        """Initializes the ViewEmail class."""
        super().__init__(config_section="gmail")

    def run(self):
        """Runs the email viewing process."""
        self.logger.info("Running ViewEmail script")

    def execute(self):
        """Executes the email viewing process."""
        self.logger.info("Executing ViewEmail script")
        self.run()  # Call the existing run method for now
        self.logger.info("ViewEmail script execution complete.")
