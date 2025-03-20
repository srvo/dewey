from dewey.core.base_script import BaseScript


class ResearchEngines(BaseScript):
    """
    Base class for research engines within Dewey.

    This class provides a standardized structure for research engines,
    including configuration loading, logging, and a `run` method to
    execute the engine's primary logic.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        """
        Executes the primary logic of the research engine.
        """
        self.logger.info("Running research engine...")
        # Add engine logic here
        engine_name = self.get_config_value("engine_name", "DefaultEngine")
        self.logger.info(f"Engine name: {engine_name}")

