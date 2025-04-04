from dewey.core.base_script import BaseScript


class CompanyAnalysis(BaseScript):
    """Analyzes company data."""

    def __init__(self):
        """Initializes the CompanyAnalysis script."""
        super().__init__(config_section="company_analysis")

    def execute(self) -> None:
        """Executes the company analysis process."""
        self.logger.info("Starting company analysis...")
        # Implement company analysis logic here
        self.logger.info("Company analysis completed.")

    def run(self) -> None:
        """
        Legacy method for backward compatibility.

        New scripts should implement execute() instead of run().
        This method will be deprecated in a future version.
        """
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        self.execute()
