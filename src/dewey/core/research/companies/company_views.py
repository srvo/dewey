from dewey.core.base_script import BaseScript


class CompanyViews(BaseScript):
    """A class to manage company views, inheriting from BaseScript."""

    def __init__(self):
        """Initializes the CompanyViews class with configurations for company views."""
        super().__init__(config_section="company_views")

    def execute(self) -> None:
        """Executes the main logic for managing company views."""
        self.logger.info("Starting company views management...")
        # Add your main logic here
        self.logger.info("Company views management completed.")

    def run(self) -> None:
        """Legacy method that calls execute() for backward compatibility."""
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
