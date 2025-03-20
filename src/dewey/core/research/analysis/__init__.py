from dewey.core.base_script import BaseScript


class AnalysisScript(BaseScript):
    """
    Base class for analysis scripts within the Dewey project.

    Inherits from BaseScript and provides a standardized structure,
    logging, and configuration for analysis-related tasks.
    """

    def __init__(self, config_section: str = "analysis") -> None:
        """
        Initializes the AnalysisScript with a configuration section.

        Args:
            config_section: The section in dewey.yaml to load for this script.
                            Defaults to "analysis".
        """
        super().__init__(config_section=config_section)

    def run(self) -> None:
        """
        Abstract method to be implemented by subclasses.

        This method contains the core logic of the analysis script.
        """
        raise NotImplementedError("Subclasses must implement the run method.")
