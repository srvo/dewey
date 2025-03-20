from dewey.core.base_script import BaseScript


class AnalysisTaggingWorkflow(BaseScript):
    """
    A workflow for analysis tagging.

    This class inherits from BaseScript and provides methods for
    tagging analysis results.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the AnalysisTaggingWorkflow."""
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        """Executes the analysis tagging workflow."""
        self.logger.info("Starting analysis tagging workflow.")
        # Access configuration values using self.get_config_value()
        tagging_enabled = self.get_config_value("analysis.tagging.enabled", True)

        if tagging_enabled:
            self.logger.info("Analysis tagging is enabled.")
            # Add your analysis tagging logic here
        else:
            self.logger.info("Analysis tagging is disabled.")
